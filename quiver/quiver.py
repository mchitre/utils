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

import os, json, sys, re, shutil, pathlib

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
    filename = os.path.join(root, 'meta.json')
    with open(filename, encoding='utf-8') as f:
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
def json2md(json, tags=[]):
  s = '---\n'
  s += 'title: '+note['title']+'\n'
  s += 'uuid: '+note['uuid']+'\n'
  s += 'notebook: '+note['notebook']+'('+note['notebook_uuid']+')\n'
  s += 'tags: '+', '.join(tags)+'\n'
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

# md to json conversion
def md2json(md):
  pass

# push handling
if verb == 'push':
  print('Not implemented yet')
  exit(1)

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
  filename = os.path.join(note['root'], 'meta.json')
  with open(filename, encoding='utf-8') as f:
    meta = json.load(f)
  filename = os.path.join(note['root'], 'content.json')
  with open(filename, encoding='utf-8') as f:
    data = json.load(f)
  print('Creating', note['uuid']+'.md')
  with open(note['uuid']+'.md', 'w') as f:
    f.write(json2md(data, meta['tags']))
  rescopy(os.path.join(note['root'], 'resources'), resources)
  exit(0)
