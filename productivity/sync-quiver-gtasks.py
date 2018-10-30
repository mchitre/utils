#!/usr/bin/python
#
# Synchronize tasks from Quiver database with Google tasks
#
# We look for @todo tags in markdown cells in Quiver notebook, and synchronize
# these with the active tasklist in Google tasks. Tasks marked with @todo(...)
# are ignored. If a @due(...) tag is present after the @todo tag, we also
# capture the due date. Deletions, completions and movements between lists in
# Google tasks are synced back. Completed tasks are marked as @done(...), while
# deleted tasks are marked as @canceled.

import os, json, re, pytz, datetime
import dateutil.parser
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from pathlib import Path

# settings
home         = str(Path.home())
quiverRoot   = home+'/Dropbox/apps/Quiver.qvlibrary'    # Quiver notebook path
cachefile    = quiverRoot+'/tasksync.json'              # Synchronization cache file
store        = home+'/.google/token-tasks.json'         # Google oauth credentials
credentials  = home+'/.google/credentials.json'         # Google oauth credentials
activelist   = 'Active'                                 # Google task list to create tasks in
trash        = 'Trash.qvnotebook'                       # Quiver trash notebook to ignore

# authenticate Google task API
store = file.Storage(store)
creds = store.get()
if not creds or creds.invalid:
  flow = client.flow_from_clientsecrets(credentials, 'https://www.googleapis.com/auth/tasks')
  creds = tools.run_flow(flow, store)
service = build('tasks', 'v1', http=creds.authorize(Http()))

# parse dates in all kinds of formats
def parse_date(due):
  try:
    return dateutil.parser.parse(due)
  except:
    return None

# delete a Google task
def delete_task(task):
  tlist, tid = task['id'].split('/')
  try:
    results = service.tasks().delete(tasklist=tlist, task=tid).execute()
  except Exception as e:
    print(e)

# create new Google tasks
def create_task(task):
  due = None
  if task['due'] is not None:
    due = parse_date(task['due'])
  body = {
    'status': 'needsAction',
    'kind': 'tasks#task',
    'title': task['title'],
    'notes': '[ '+task['note']+' ]'
  }
  if due is not None:
    body['due'] = due.astimezone(pytz.utc).isoformat('T')
  try:
    results = service.tasks().insert(tasklist=activelist, body=body).execute()
    return activelist+'/'+results['id']
  except Exception as e:
    print(e)
    return None

# populate id in task if task exists in tlist, and remove from tlist
def find_task(tlist, task):
  for t in tlist:
    if 'id' in t:
      task['id'] = t['id']
      if t == task:
        tlist.remove(t)
        return
      del task['id']

# change task id in database
def update_tid(db, old, new):
  for file in db:
    for item in db[file]:
      if 'id' in item and item['id'] == old:
        item['id'] = new

# remove todo markup in Quiver markdown documents
def remove_todo(tid, done):
  global qtodo
  qtodo2 = {}
  for file in qtodo:
    items = []
    for item in qtodo[file]:
      if 'id' in item and item['id'] == tid:
        with open(file, encoding='utf-8') as f:
          data = json.load(f)
        for cell in data['cells']:
          if cell['type'] == 'markdown':
            lines = cell['data'].splitlines()
            i = 0
            for line in lines:
              if re.search(r'\s@todo\s', line+' '):
                title = re.match(r'^[\-\*]?(.*)\s@todo\s.*$', line.strip()+' ')[1].strip()
                if re.match(r'^\[.\]', title):
                  title = title[3:].strip()
                if title == item['title']:
                  if not done:
                    line = re.sub(r'\s@todo\s', ' @canceled ', line+' ').rstrip()
                  else:
                    line = re.sub(r'\s@todo\s', ' @done('+done+') ', line+' ').rstrip()
                    line = line.replace('- [ ] ', '- [x] ')
                  lines[i] = line
              i = i+1
            cell['data'] = '\n'.join(lines)
        with open(file, 'w', encoding='utf-8') as f:
          json.dump(data, f)
      else:
        items.append(item)
    if len(items) > 0:
      qtodo2[file] = items
  qtodo = qtodo2

# read synchronization cache
qtodo_cached = {}
lastrun = 0
if os.path.isfile(cachefile):
  lastrun = mtime = os.path.getmtime(cachefile)
  with open(cachefile, encoding='utf-8') as f:
    qtodo_cached = json.load(f)

# extract tasks from Quiver database
qtodo = {}
for root, subdirs, files in os.walk(quiverRoot):
  if trash in root:
    continue
  if 'content.json' in files:
    filename = os.path.join(root, 'content.json')
    mtime = os.path.getmtime(filename)
    if mtime < lastrun:
      if filename in qtodo_cached:
        qtodo[filename] = qtodo_cached[filename]
        del qtodo_cached[filename]
    else:
      with open(filename, encoding='utf-8') as f:
        data = json.load(f)
      t = []
      for cell in data['cells']:
        if cell['type'] == 'markdown':
          for line in cell['data'].splitlines():
            if re.search(r'\s@todo\s', line+' '):
              title = re.match(r'^[\-\*]?(.*)\s@todo\s.*$', line.strip()+' ')[1].strip()
              if re.match(r'^\[.\]', title):
                title = title[3:].strip()
              due = re.search(r'\s@due\(([^\)]+)\)', line)
              if due is not None:
                due = due[1]
              task = { 'note': data['title'], 'title': title, 'due': due }
              if filename in qtodo_cached:
                find_task(qtodo_cached[filename], task)
              t.append(task)
      if len(t) > 0:
        qtodo[filename] = t

# get Google tasks
after = datetime.datetime.fromtimestamp(int(lastrun)).astimezone(pytz.utc).isoformat('T')
gtask_added = {}
gtask_deleted = {}
gtask_moved = {}
results = service.tasklists().list().execute()
items = results.get('items', [])
for item in items:
  if item['title'] == activelist:
    activelist = item['id']
  results = service.tasks().list(tasklist=item['id'], showCompleted=True, showDeleted=True, updatedMin=after).execute()
  items2 = results.get('items', [])
  for item2 in items2:
    if 'deleted' in item2 and item2['deleted']:
      if item2['title'] in gtask_added:
        gtask_moved[item['id']+'/'+item2['id']] = gtask_added[item2['title']]
        del gtask_added[item2['title']]
      else:
        gtask_deleted[item2['title']] = item['id']+'/'+item2['id']
    elif 'completed' in item2 and item2['completed']:
      remove_todo(item['id']+'/'+item2['id'], item2['completed'][:10])
    else:
      if item2['title'] in gtask_deleted:
        gtask_moved[gtask_deleted[item2['title']]] = item['id']+'/'+item2['id']
        del gtask_deleted[item2['title']]
      else:
        gtask_added[item2['title']] = item['id']+'/'+item2['id']

# rename moved Google tasks in synchronization database
for item in gtask_moved:
  update_tid(qtodo, item, gtask_moved[item])
  update_tid(qtodo_cached, item, gtask_moved[item])

# update Google task deletions in Quiver notebook
for item in gtask_deleted:
  remove_todo(gtask_deleted[item], False)

# remove deleted Quiver todos from Google tasks
for file in qtodo_cached:
  for task in qtodo_cached[file]:
    if 'id' in task:
      delete_task(task)

# create new Google tasks for new Quiver todos
for file in qtodo:
  for task in qtodo[file]:
    if 'id' not in task:
      tid = create_task(task)
      if tid is not None:
        task['id'] = tid

# write synzhronization cache
with open(cachefile, 'w', encoding='utf-8') as f:
  json.dump(qtodo, f)
