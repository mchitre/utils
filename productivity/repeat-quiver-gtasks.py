#/usr/bin/python
#
# Schedule repeated chores to Google tasks based on Quiver notebook
#
# We look for @repeat(...) tags to find tasks to be scheduled regularly.
# Examples:
#   - Schedule something every Monday @repeat(weekday=1)
#   - Do something urgent every Tuesday @repeat(weekday=1, due=+1)
#   - Do something every month @repeat(day=1)
#   - Do something every year @repeat(month=2, day=14)

import os, json, re, datetime, pytz
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from pathlib import Path

# settings
home         = str(Path.home())
quiverRoot   = home+'/Dropbox/apps/Quiver.qvlibrary'    # Quiver notebook path
store        = home+'/.google/token-tasks.json'         # Google oauth credentials
credentials  = home+'/.google/credentials.json'         # Google oauth credentials
inbox        = 'Inbox'                                  # default list for repeated tasks
trash        = 'Trash.qvnotebook'                       # Quiver trash notebook to ignore

# authenticate Google task API
store = file.Storage(store)
creds = store.get()
if not creds or creds.invalid:
  flow = client.flow_from_clientsecrets(credentials, 'https://www.googleapis.com/auth/tasks')
  creds = tools.run_flow(flow, store)
service = build('tasks', 'v1', http=creds.authorize(Http()))

# extract tasks from Quiver database
tasks = []
regex = re.compile(r'\b(\w+)\b\s*=\s*([\-\+\.0-9a-zA-Z]+)')
today = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
for root, subdirs, files in os.walk(quiverRoot):
  if trash in root:
    continue
  if 'content.json' in files:
    filename = os.path.join(root, 'content.json')
    with open(filename, encoding='utf-8') as f:
      data = json.load(f)
    t = []
    for cell in data['cells']:
      if cell['type'] == 'markdown':
        for line in cell['data'].splitlines():
          if re.search(r'\s@repeat\(.*\)', line):
            m = re.match(r'^[\-\*]?(.*)\s@repeat\(([^\)]*)\).*$', line.strip())
            title = m[1].strip()
            criteria = m[2].strip()
            due = None
            matches = True
            tlist = inbox
            for m in regex.finditer(criteria):
              if m[1] != 'list':
                try:
                  v = float(m[2])
                except:
                  print('Bad value:', m[1]+'='+m[2])
                  v = 0
              if m[1] == 'weekday':
                if today.isoweekday() != v:
                  matches = False
              elif m[1] == 'day':
                if today.day != v:
                  matches = False
              elif m[1] == 'month':
                if today.month != v:
                  matches = False
              elif m[1] == 'due':
                due = today + datetime.timedelta(days=v)
              elif m[1] == 'list':
                tlist = m[2]
              else:
                print('Bad keyword:', m[1]+'='+m[2])
            if matches:
              tasks.append((title, due, tlist))

# get Google list ids
results = service.tasklists().list().execute()
items = results.get('items', [])
lists = {}
for item in items:
  lists[item['title']] = item['id']

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
    if task[2] in lists:
      tlist = lists[task[2]]
    else:
      print('Bad list:', task[2])
      tlist = lists[inbox] if inbox in lists else list(lists.values())[0]
    service.tasks().insert(tasklist=tlist, body=body).execute()
  except Exception as e:
    print(body)
    print(e)
