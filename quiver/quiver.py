#!/usr/bin/python
#
# Work with Quiver notes as markdown documents
#
# Usage:
#   quiver.py list [<notebook-regex>] [<title-regex>]
#   quiver.py pull [<notebook-regex>] [<title-regex>]
#   quiver.py push <markdown-file>
#
# We search the Quiver database for the matching notebook and note title.
# A hyphen may be used in place of the <notebook-regex> to match all notebooks.
# If a single note is matched, it can be exported in markdown format. If multiple
# matches are found, a list of matching notes is displayed.
#
# The markdown format uses a yaml header with meta information, and "---"
# separated sections for Quiver cells. Code cells are enclosed in "```", while
# all other cells are enclosed in a html "<div>" tag with appropriate attributes
# inheritted from the JSON cells in Quiver. All resources are copied into a
# "resources" folder.

import os, json, sys, re, shutil, pathlib, uuid, time

# settings
home         = str(pathlib.Path.home())
quiverRoot   = home+'/Dropbox/apps/Quiver.qvlibrary'     # Quiver notebook path
trash        = 'Trash.qvnotebook'                        # Quiver trash notebook to ignore
resources    = 'resources'                               # name or resource folder

# usage
def usage():
  print('''
Usage:
  quiver.py list [<notebook-regex>] [<title-regex>]
  quiver.py pull [<notebook-regex>] [<title-regex>]
  quiver.py push <markdown-file>
''')
  exit(1)

# arguments
nargs = len(sys.argv)
if nargs < 2 or nargs > 4:
  usage()
verb = sys.argv[1]
if verb not in ['list', 'pull', 'push']:
  usage()
if verb == 'push':
  if nargs != 3:
    usage()
  filename = sys.argv[2]
else:
  nb_regex = '-'
  note_regex = '-'
  if nargs > 2:
    nb_regex = sys.argv[2]
  if nargs > 3:
    note_regex = sys.argv[3]

# get list of notes
notebook = ''
notebook_uuid = ''
notes = []
for root, subdirs, files in os.walk(quiverRoot):
  if trash in root:
    continue
  if 'meta.json' in files:
    fname = os.path.join(root, 'meta.json')
    with open(fname, encoding='utf-8') as f:
      data = json.load(f)
    if root.endswith('qvnotebook') and 'name' in data:
      notebook = data['name']
      notebook_uuid = data['uuid']
    elif root.endswith('qvnote') and 'title' in data:
      notes.append({
        'notebook': notebook,
        'notebook_uuid': notebook_uuid,
        'title': data['title'],
        'uuid': data['uuid'],
        'root': root
      })

# print list of notes
def print_list(notes):
  if len(notes) == 0:
    print('No matching notes')
  else:
    for note in notes:
      print(note['notebook'], '::', note['title'])

# copy resources
def rescopy(src, dst):
  if os.path.isdir(src):
    try:
      os.mkdir(dst)
    except:
      pass
    for f in os.listdir(src):
      out = os.path.join(dst, f)
      print('Creating', out)
      shutil.copyfile(os.path.join(src, f), out)

# json to md conversion
#   params: content.json (dictionary), meta.json (dictionary)
#   returns: markdown string
def quiver2md(json, tags={'tags': []}):
  s = '---\n'
  s += 'title: '+note['title']+'\n'
  s += 'uuid: '+note['uuid']+'\n'
  s += 'notebook: '+note['notebook']+' ('+note['notebook_uuid']+')\n'
  s += 'tags: '+', '.join(meta['tags'])+'\n'
  s += 'created: '+meta['created_at']
  s += '---\n\n'
  count = 0
  for cell in data['cells']:
    if count > 0:
      s += '\n---\n\n'
    if cell['type'] == 'markdown':
      x = cell['data']
      x = x.replace('](quiver-image-url/', ']('+resources+'/')
      s += x+'\n'
    elif cell['type'] == 'code':
      s += '```\n'
      s += cell['data']+'\n'
      s += '```\n'
    else:
      hdr = dict(cell)
      del hdr['data']
      s += '<div'
      for k in hdr.keys():
        s += ' '+k+'="'+hdr[k]+'"'
      s += '>\n'
      x = cell['data']
      if cell['type'] == 'text':
        x = x.replace('img src="quiver-image-url/', 'img src="'+resources+'/')
      s += x+'\n'
      s += '</div>\n'
    count += 1
  s += '\n'
  return s

# check if a string is a yaml header
def isyaml(s):
  lines = s.split('\n')
  for line in lines:
    if len(line) > 0 and not re.match(r'^\w+:', line):
      return False
  return True

# md to json conversion
#   params: md (markdown string)
#   returns: folder (string), meta.json (dictionary), content.json (dictionary)
def md2quiver(md, ctime=time.time(), mtime=time.time()):
  cells = md.split('---\n')
  yaml = {
    'title': '',
    'uuid': str(uuid.uuid4()).upper(),
    'notebook': 'Inbox (Inbox)',
    'tags': [],
    'created': ctime
  }
  if len(cells) > 2 and cells[0] == '' and isyaml(cells[1]):
    for s in cells[1].split('\n'):
      m = re.match(r'^(\w+): *(.*)$', s)
      if m:
        yaml[m[1]] = m[2]
    cells = cells[2:]
  nb = yaml['notebook']
  m = re.match(r'^.*\((.*)\)$', nb)
  if m:
    nb = m[1]
  fname = os.path.join(nb+'.qvnotebook', yaml['uuid']+'.qvnote')
  meta = {
    'title': yaml['title'],
    'tags': yaml['tags'].split(r'\w*,\w*'),
    'created_at': int(yaml['created']),
    'updated_at': int(mtime),
    'uuid': yaml['uuid']
  }
  content = {
    'title': yaml['title'],
    'cells': []
  }
  cells = [re.sub(r'\n$', '', re.sub(r'^\n', '', s)) for s in cells]
  for cell in cells:
    # TODO: support for other cell types
    content['cells'].append({ 'type': 'markdown', 'data': cell })
  return fname, meta, content

# push handling
if verb == 'push':
  ctime = os.path.getctime(filename)
  mtime = os.path.getmtime(filename)
  with open (filename, encoding='utf-8') as f:
    md = f.readlines()
  md = [s.rstrip() for s in md]
  md = '\n'.join(md)
  folder, meta, content = md2quiver(md, ctime, mtime)
  # TODO: write to files
  exit(0)

# filter by notebook
if nb_regex != '-':
  regex = re.compile(r'%s'%nb_regex, re.IGNORECASE)
  notes = [n for n in notes if re.search(regex, n['notebook'])]

# filter by note title
if note_regex != '-':
  regex = re.compile(r'%s'%note_regex, re.IGNORECASE)
  notes = [n for n in notes if re.search(regex, n['title'])]

# show notes
if verb == 'list':
  print_list(notes)
  exit(0)

# pull handling
if verb == 'pull':
  if len(notes) < 1:
    print('No matching notes')
    exit(2)
  elif len(notes) > 1:
    print('Too many matching notes')
    exit(2)
  note = notes[0]
  fname = os.path.join(note['root'], 'meta.json')
  with open(fname, encoding='utf-8') as f:
    meta = json.load(f)
  fname = os.path.join(note['root'], 'content.json')
  with open(fname, encoding='utf-8') as f:
    content = json.load(f)
  print('Creating', note['uuid']+'.md')
  with open(note['uuid']+'.md', 'w') as f:
    f.write(quiver2md(content, meta))
  rescopy(os.path.join(note['root'], 'resources'), resources)
  exit(0)
