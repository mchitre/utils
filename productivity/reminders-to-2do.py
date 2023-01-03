#/usr/bin/python
#
# Move reminders from Apple Reminders app to 2Do tasks
#
# We only copy the title of the reminder and the due date, as this script is
# primarily to facilitate use of Siri to add reminders to 2Do tasks, and
# Siri does not typically populate other reminder fields.

from subprocess import Popen, PIPE
import dateutil.parser, urllib.parse, re, os

# settings
inbox        = 'Inbox'                            # Apple Reminders list to copy from

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

# create 2Do tasks
for rtask in tasks:
  task = {
    'task': rtask[0],
    'type': 0,
    'ignoreDefaults': 1,
    'edit': 0,
    'forList': 'Inbox'
  }
  if rtask[1] is not None:
    task['due'] = rtask[1].strftime('%Y-%m-%d')
  q = urllib.parse.urlencode(task).replace('+', '%20')
  #print('open \'twodo://x-callback-url/add?' + q + '\'')
  os.system('open \'twodo://x-callback-url/add?' + q + '\'')
