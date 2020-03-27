import requests, os, os.path, urllib.parse, re

# settings
folder = '~/.github2do'

# load auth details
folder = os.path.expanduser(folder)
auth = [s.strip() for s in open(folder+'/auth.txt', 'rt')]
auth = tuple(auth[:2])

issues = dict()

# read all issues from github
r = requests.get('https://api.github.com/issues', auth=auth)
if r.status_code == 200:
  for issue in r.json():
    issues[issue['id']] = issue
if 'link' in r.headers:
  pages = { rel[6:-1]: url[url.index('<')+1:-1] for url, rel in (link.split(';') for link in r.headers['link'].split(',')) }
  while 'last' in pages and 'next' in pages:
    pages = { rel[6:-1]: url[url.index('<')+1:-1] for url, rel in (link.split(';') for link in r.headers['link'].split(',')) }
    r = requests.get(pages['next'], auth=auth)
    if r.status_code == 200:
      for issue in r.json():
        issues[issue['id']] = issue
    if pages['next'] == pages['last']:
      break

# simulate getting data from github.com
# for s in open('github.dump', 'rt'):
#   issue = eval(s)
#   issues[issue['id']] = issue
#   print(issue['id'], ':', issue['title'])

# make a list of issues
iset = set()
for i in issues.values():
  iset.add(i['id'])

# create folder to cache issue list
try:
  os.mkdir(folder)
except:
  pass

# load old issue list from disk
oiset = set()
try:
  with open(folder+'/issues.txt', 'rt') as f:
    oiset = eval(f.read())
except ex:
  pass

# go through new issues and make tasks
for i in iset.difference(oiset):
  issue = issues[i]
  task = {
    'task': issue['title'],
    'action': 'url:'+re.sub(r'\\n', '', issue['html_url']),
    'type': 0,
    'ignoreDefaults': 1,
    'edit': 0,
    'tags': 'github',
    'forList': 'Inbox'
  }
  q = urllib.parse.urlencode(task).replace('+', '%20')
  #print('open \'twodo://x-callback-url/add?' + q + '\'')
  os.system('open \'twodo://x-callback-url/add?' + q + '\'')

# write latest issue list to disk
with open(folder+'/issues.txt', 'wt') as f:
  f.write(str(iset))
