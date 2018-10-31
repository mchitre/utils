import os, calendar, re, uuid, time, pytz
import dateutil.parser

# json to md conversion
#   params: content.json (dictionary), meta.json (dictionary)
#   returns: markdown string
def quiver2md(content, meta={'tags': []}, note=None, resourceDir='resources'):
  s = '---\n'
  s += 'title: '+meta['title']+'\n'
  s += 'uuid: '+meta['uuid']+'\n'
  if note:
    s += 'notebook: '+note['notebook']+' ('+note['notebook_uuid']+')\n'
  s += 'tags: '+', '.join(meta['tags'])+'\n'
  s += 'created: '+str(meta['created_at'])+'\n'
  s += '---\n\n'
  count = 0
  for cell in content['cells']:
    if count > 0:
      s += '\n---\n\n'
    if cell['type'] == 'markdown':
      x = cell['data']
      x = x.replace('](quiver-image-url/', ']('+resourceDir+'/')
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
        x = x.replace('img src="quiver-image-url/', 'img src="'+resourceDir+'/')
      s += x+'\n'
      s += '</div>\n'
    count += 1
  s += '\n'
  return s

# check if a string is a yaml header
def _isyaml(s):
  lines = s.split('\n')
  for line in lines:
    if len(line) > 0 and not re.match(r'^\w+:', line):
      return False
  return True

# convert various date formats to epoch time
def _epoch(s):
  try:
    return int(s)
  except:
    pass
  try:
    dts = dateutil.parser.parse(s)
    return calendar.timegm(dts.astimezone(pytz.utc).timetuple())
  except Exception as ex:
    pass
  try:
    return calendar.timegm(dts.timetuple())  # seems to be needed for Editorial on iPad
  except Exception as ex:
    pass
  return 0

# md to json conversion
#   params: md (markdown string)
#   returns: folder (string), meta.json (dictionary), content.json (dictionary), resources (dictionary)
def md2quiver(md, ctime=time.time(), mtime=time.time(), title='', resourceDir='resources'):
  resources = {}
  cells = md.split('---\n')
  yaml = {
    'title': title,
    'uuid': str(uuid.uuid4()).upper(),
    'notebook': 'Inbox (Inbox)',
    'tags': None,
    'created': ctime
  }
  if len(cells) > 2 and cells[0] == '' and _isyaml(cells[1]):
    for s in cells[1].split('\n'):
      m = re.match(r'^(\w+): *(.*)$', s)
      if m:
        yaml[m.group(1)] = m.group(2)
    cells = cells[2:]
  nb = yaml['notebook']
  m = re.match(r'^.*\((.*)\)$', nb)
  if m:
    nb = m.group(1)
  fname = os.path.join(nb+'.qvnotebook', yaml['uuid']+'.qvnote')
  meta = {
    'title': yaml['title'],
    'tags': [s.strip() for s in yaml['tags'].split(r',')] if yaml['tags'] else [],
    'created_at': _epoch(yaml['created']),
    'updated_at': int(mtime),
    'uuid': yaml['uuid']
  }
  content = {
    'title': yaml['title'],
    'cells': []
  }
  cells = [re.sub(r'\n$', '', re.sub(r'^\n', '', s)) for s in cells]
  for cell in cells:
    s = cell.strip()
    if s.startswith('```\n') and s.endswith('\n```'):
      content['cells'].append({ 'type': 'code', 'data': cell[4:-4] })
    elif s.startswith('<div') and s.endswith('</div>'):
      cell = re.sub(r'^<div[^>]*>\s*', '', cell)
      cell = re.sub(r'\s*</div>$', '', cell)
      cell = cell.replace('img src="'+resourceDir+'/', 'img src="quiver-image-url/')
      rlist = re.findall(r'img src="quiver-image-url/([^"]*)"', cell)
      for r in rlist:
        resources[r] = r
      data = { 'data': cell }
      m = re.match(r'^<div\s+([^>]*) *>', s)
      s = m.group(1)
      m = re.match(r'^\s*(\w+)\s*=\s*"([^"]*)"', s)
      while m:
        data[m.group(1)] = m.group(2)
        s = s[len(m.group(0)):]
        m = re.match(r'^\s*(\w+)\s*=\s*"([^"]*)"', s)
      content['cells'].append(data)
    else:
      cell = cell.replace(']('+resourceDir+'/', '](quiver-image-url/')
      rlist = re.findall(r'quiver-image-url/([^\)]*)\)', cell)
      for r in rlist:
        resources[r] = r
      content['cells'].append({ 'type': 'markdown', 'data': cell })
  return fname, meta, content, resources
