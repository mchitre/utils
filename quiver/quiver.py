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

import os, json, sys, re, pathlib
from quiverlib import rescopy, quiver2md, md2quiver

# settings
home         = str(pathlib.Path.home())
quiverRoot   = home+'/Dropbox/apps/Quiver.qvlibrary'     # Quiver notebook path
trash        = 'Trash.qvnotebook'                        # Quiver trash notebook to ignore
resourceDir  = 'resources'                               # name or resource folder

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

# print list of notes
def print_list(notes):
  if len(notes) == 0:
    print('No matching notes')
  else:
    for note in notes:
      print(note['notebook'], '::', note['title'])

# push handling
if verb == 'push':
  ctime = os.path.getctime(filename)
  mtime = os.path.getmtime(filename)
  with open(filename, encoding='utf-8') as f:
    md = f.readlines()
  md = [s.rstrip() for s in md]
  md = '\n'.join(md)
  _, fname = os.path.split(filename)
  fname = re.sub(r'\.[^\.]*$', '', fname)
  folder, meta, content, resources = md2quiver(md, ctime, mtime, fname, resourceDir)
  try:
    fname = os.path.join(quiverRoot, folder)
    os.mkdir(fname)
  except:
    pass
  fname = os.path.join(quiverRoot, folder, 'meta.json')
  print('Writing', os.path.join(folder, 'meta.json'))
  with open(fname, 'w', encoding='utf-8') as f:
    f.write(json.dumps(meta, indent=2))
  fname = os.path.join(quiverRoot, folder, 'content.json')
  print('Writing', os.path.join(folder, 'content.json'))
  with open(fname, 'w', encoding='utf-8') as f:
    f.write(json.dumps(content, indent=2))
  if len(resources) > 0:
    copied = rescopy(resourceDir, os.path.join(quiverRoot, folder, 'resources'), resources)
    for f in copied.keys():
      f1 = copied[f]
      if f == f1:
        print('Copying', f)
      else:
        print('Copying', f, '=>', f1)
  exit(0)

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
  print('Writing', note['uuid']+'.md')
  with open(note['uuid']+'.md', 'w') as f:
    f.write(quiver2md(content, meta, note, resourceDir))
  copied = rescopy(os.path.join(note['root'], 'resources'), resourceDir)
  for f in copied.keys():
    f1 = copied[f]
    if f == f1:
      print('Copying', f)
    else:
      print('Copying', f, '=>', f1)
  exit(0)
