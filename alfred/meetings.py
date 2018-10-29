#!/Users/mandar/anaconda3/bin/python

import datetime, time
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

store = file.Storage('/Users/mandar/.google/token-cal.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('/Users/mandar/.google/credentials.json', 'https://www.googleapis.com/auth/calendar.readonly')
    creds = tools.run_flow(flow, store)
service = build('calendar', 'v3', http=creds.authorize(Http()))

now = datetime.datetime.utcnow()
start = now - datetime.timedelta(hours=8)
end = now + datetime.timedelta(hours=8)
events_result = service.events().list(calendarId='primary',
                                    timeMin=start.isoformat()+'Z',
                                    timeMax=end.isoformat()+'Z',
                                    singleEvents=True,
                                    orderBy='startTime').execute()
events = events_result.get('items', [])

print('{ "items": [')
for event in events:
    start = event['start'].get('dateTime', event['start'].get('date'))
    start = start[:10] + ' ' + start[11:19]
    dts = time.strptime(start, '%Y-%m-%d %H:%M:%S')
    dts = '%02d/%02d %02d:%02d'%(dts[2],dts[1],dts[3],dts[4])
    title = event['summary']
    print('  { "title": "'+title+'", "subtitle": "'+dts+'", "arg": "'+title+'" },')
print(']}')

