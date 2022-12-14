#!/usr/bin/python3

import json, re, sys

FILE='/Users/mandar/GDrive/Apps/Quiver/Quiver.qvlibrary/D7D4B4F5-01DF-4C64-960C-1003216F466B.qvnotebook/F4A197BD-6A2E-4E34-9094-1B5F596FCE9C.qvnote/content.json'

with open(FILE) as f:
  s = json.load(f)

print('{"items": [')
data = s['cells'][0]['data']
for line in data.split('\n'):
  k, v = line.split(':')
  k = re.sub(r'^\*', '', k).strip()
  v = v.strip()
  if re.search(r'%s' % sys.argv[1], k, re.IGNORECASE):
    print('  {"uid": "'+k+'", "arg": "'+v+'", "title": "'+k+'", "subtitle": "'+v+'"},')
print(']}')
