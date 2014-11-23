# -*- coding: utf-8 -*-
import os
import json
import datetime
from googleapiclient.http import BatchHttpRequest
import httplib2
from googleapiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
import rfc3339

class GoogleCalendar:

    _scope = 'https://www.googleapis.com/auth/calendar'

    def __init__(self, key_p12_path, service_account_mail):

        if not os.path.exists(key_p12_path):
            raise AttributeError('p12 key path is not vaild')

        f = file(key_p12_path, 'rb')
        key = f.read()
        f.close()

        credentials = SignedJwtAssertionCredentials(
            service_account_mail,
            key,
            scope=self._scope)

        http = httplib2.Http()
        self._http = credentials.authorize(http)
        self._service = build('calendar', 'v3', http=http)
        # batch is limited up to 1000 queries in one
        self._batch = BatchHttpRequest()
        self._calendar_id = None
        self._event_json_path = None
        self._event_name_to_id_dict = None
        self._service_mail = service_account_mail

    def commitChanges(self):
        self._batch.execute(http=self._http)

    def eventAdded(self, request_id, response, exception):

        if exception is None:
            self._event_name_to_id_dict[request_id] = response['id']
        else:
            pass

    def addScheduleEvents(self, event_names, event_details):

        for ev_name in event_names:
            s_date = event_details[ev_name][u'Data rozpoczęcia'.encode('windows-1250')]
            s_time = event_details[ev_name][u'Czas rozpoczęcia'.encode('windows-1250')]

            e_date = event_details[ev_name][u'Data zakończenia'.encode('windows-1250')]
            e_time = event_details[ev_name][u'Czas zakończenia'.encode('windows-1250')]

            event = {
                'summary': ev_name.decode('windows-1250'),

                'start': {
                    'dateTime': rfc3339.rfc3339(datetime.datetime(int(s_date[:4]),
                                                                  int(s_date[5:7]),
                                                                  int(s_date[8:10]),
                                                                  int(s_time[:2]),
                                                                  int(s_time[3:5])))
                },
                'end': {
                    'dateTime': rfc3339.rfc3339(datetime.datetime(int(e_date[:4]),
                                                                  int(e_date[5:7]),
                                                                  int(e_date[8:10]),
                                                                  int(e_time[:2]),
                                                                  int(e_time[3:5])))
                },
            }

            loc = event_details[ev_name][u'Lokalizacja'.encode('windows-1250')]

            # sprawdzic co to jest null np przy jezykach
            if loc is not None:
                event['location'] = loc

            if '(w)' in ev_name:
                col = '10'
            elif '(L)' in ev_name:
                col = '4'
            elif '(p)' in ev_name:
                col = '6'
            elif u'(ć)'.encode('windows-1250') in ev_name:
                col = '11'
            else:
                col = '1'

            event['colorId'] = col
            self._batch.add(self._service.events().insert(calendarId=self._calendar_id, body=event), callback=self.eventAdded, request_id=ev_name)

    def modifyScheduleEvents(self, event_name, old_event_details, new_event_details):
        pass

    def removeScheduleEvents(self, event_name):
        pass

    def mailAboutChanges(self, mail):
        pass

    def createCalendar(self, name):
        calendar = {
            'summary': name,
            'timeZone': 'Europe/Warsaw'
        }

        created_calendar = self._service.calendars().insert(body=calendar).execute()

        return created_calendar['id']

    def setCalendar(self, calendar_id, event_dict_json_path):
        self._calendar_id = calendar_id
        self._event_json_path = event_dict_json_path
        self._event_name_to_id_dict = json.loads(open(event_dict_json_path).read(), encoding='windows-1250') if os.path.exists(event_dict_json_path) else {}

    def shareCalendarWithGroup(self, email):
        rule = {
            'scope': {
                'type': 'group',
                'value': email,
            },
            'role': 'reader'
        }

        created_rule = self._service.acl().insert(calendarId=self._calendar_id, body=rule).execute()

        return created_rule['id']

    def shareCalendarWithOwner(self, email):
        grant = {
            'scope': {
                'type': 'user',
                'value': email,
            },
            'role': 'owner'
        }
        created_rule = self._service.acl().insert(calendarId=self._calendar_id, body=grant).execute()
        return created_rule['id']

    def deletePrivileges(self, acl_id):
        self._service.acl().delete(calendarId=self._calendar_id, ruleId=acl_id).execute()

    def clearCalendar(self):
        self._service.calendars().clear(calendarId=self._calendar_id).execute()

    def end(self):
        json_file = open(self._event_json_path, mode='w')
        # ensure_ascii=False cause of utf coding problems
        json_file.write(json.dumps(self._event_name_to_id_dict, encoding='windows-1250'))
        json_file.close()