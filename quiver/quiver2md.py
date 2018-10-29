#!/usr/bin/python
#
# Extract Quiver note as markdown
#
# Usage:
#   quiver2md.py [notebook-regex] [title-regex]
#
# We search the Quiver database for the matching notebook and note title.
# A hyphen may be used in place of the notebook-regex to match all notebooks.
# If a single note is matched, it is exported in markdown format. If multiple
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

# filter by notebook
if len(sys.argv) > 1 and sys.argv[1] != '-':
  regex = re.compile(r'%s'%sys.argv[1], re.IGNORECASE)
  notes = [n for n in notes if re.search(regex, n['notebook'])]

# filter by note title
if len(sys.argv) > 2 and sys.argv[2] != '-':
  regex = re.compile(r'%s'%sys.argv[2], re.IGNORECASE)
  notes = [n for n in notes if re.search(regex, n['title'])]

# no matching notes, stop!
if len(notes) == 0:
  print('No matching notes')
  exit(1)

# too many matching notes, stop!
if len(notes) > 1:
  print('# Notes')
  for note in notes:
    print('-', note['notebook'], '::', note['title'])
  exit(2)

# read the note
note = notes[0]
filename = os.path.join(note['root'], 'meta.json')
with open(filename, encoding='utf-8') as f:
  meta = json.load(f)
filename = os.path.join(note['root'], 'content.json')
with open(filename, encoding='utf-8') as f:
  data = json.load(f)

# export to file
print('Output:', note['uuid']+'.md')
with open(note['uuid']+'.md', 'w') as f:

  # yaml block
  f.write('---\n')
  f.write('title: '+note['title']+'\n')
  f.write('uuid: '+note['uuid']+'\n')
  f.write('notebook: '+note['notebook']+'('+note['notebook_uuid']+')\n')
  f.write('tags: '+', '.join(meta['tags'])+'\n')
  f.write('---\n\n')

  # export cells
  count = 0
  for cell in data['cells']:
    if count > 0:
      f.write('\n---\n\n')
    if cell['type'] == 'markdown':
      x = cell['data']
      x = x.replace('](quiver-image-url/', ']('+resources+'/')
      f.write(x+'\n')
    elif cell['type'] == 'code':
      f.write('```\n')
      f.write(cell['data']+'\n')
      f.write('```\n')
    else:
      hdr = dict(cell)
      del hdr['data']
      f.write('<div')
      for k in hdr.keys():
        f.write(' '+k+'="'+hdr[k]+'"')
      f.write('>\n')
      x = cell['data']
      if cell['type'] == 'text':
        x = x.replace('img src="quiver-image-url/', 'img src="'+resources+'/')
      f.write(x+'\n')
      f.write('</div>\n')
    count = count + 1

  # done
  f.write('\n')

# copy resources out
src_resources = os.path.join(note['root'], 'resources')
try:
  os.mkdir(resources)
except:
  pass
for f in os.listdir(src_resources):
  print('Resource:', f)
  shutil.copyfile(os.path.join(src_resources, f), os.path.join(resources, f))
