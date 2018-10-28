#/usr/bin/python
#
# Move reminders from Apple Reminders app to Google tasks
#
# We only copy the title of the reminder and the due date, as this script is
# primarily to facilitate use of Siri to add reminders to Google tasks, and
# Siri does not typically populate other reminder fields.

from subprocess import Popen, PIPE
import pytz
import dateutil.parser
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from pathlib import Path

# settings
home         = str(Path.home())
store        = home+'/.google/token-tasks.json'   # Google oauth credentials
credentials  = home+'/.google/credentials.json'   # Google oauth credentials
inbox        = 'Inbox'                            # Apple Reminders list to copy from
activelist   = 'Active'                           # Google task list to copy task to

# authenticate Google task API
store = file.Storage(store)
creds = store.get()
if not creds or creds.invalid:
  flow = client.flow_from_clientsecrets(credentials, 'https://www.googleapis.com/auth/tasks')
  creds = tools.run_flow(flow, store)
service = build('tasks', 'v1', http=creds.authorize(Http()))

# Applescript to get reminders from Apple Reminders and delete them
scpt = '''
  set out to ""
  tell application "Reminders"
    set mylist to (every reminder in list "#INBOX#" whose completed is false)
    repeat with r in mylist
      set out to out & (name of r as string) & "|" & (due date of r as string) & "
"
      delete r
    end repeat
  end tell
  return out
'''.replace('#INBOX#', inbox)

# run apple script and capture output
p = Popen(['osascript'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
stdout, stderr = p.communicate(scpt.encode('utf-8'))
out = stdout.decode('utf-8')
if p.returncode != 0:
  err = stderr.decode('utf-8')
  print(p.returncode, out, err)
  exit(1)
tasks = []
for line in out.splitlines():
  if '|' in line:
    title, due = line.split('|')
    if due == 'missing value':
      due = None
    else:
      due = dateutil.parser.parse(due)
    tasks.append((title, due))

# get Google active list id
results = service.tasklists().list().execute()
items = results.get('items', [])
for item in items:
  if item['title'] == activelist:
    activelist = item['id']

# create Google tasks
for task in tasks:
  body = {
    'status': 'needsAction',
    'kind': 'tasks#task',
    'title': task[0],
  }
  if task[1] is not None:
    body['due'] = task[1].astimezone(pytz.utc).isoformat('T')
  try:
    service.tasks().insert(tasklist=activelist, body=body).execute()
  except Exception as e:
    print(body)
    print(e)
