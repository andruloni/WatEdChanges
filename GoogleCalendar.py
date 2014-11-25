# -*- coding: utf-8 -*-
import os
import json
import datetime
from googleapiclient.http import BatchHttpRequest
import httplib2
from googleapiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from DictDiffer import DictDiffer
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

    def pushChanges(self):
        self._batch.execute(http=self._http)

    def eventAdded(self, request_id, response, exception):

        if exception is None:
            self._event_name_to_id_dict[request_id] = response['id']
        else:
            pass

    def eventModified(self, request_id, response, exception):
        pass

    def _convertDateTime(self, date, time):
        return rfc3339.rfc3339(datetime.datetime(int(date[:4]),
                                                 int(date[5:7]),
                                                 int(date[8:10]),
                                                 int(time[:2]),
                                                 int(time[3:5])))

    def _eventStartDateTime(self, event_details):
        return self._convertDateTime(event_details[u'Data rozpoczęcia'.encode('windows-1250')],
                                     event_details[u'Czas rozpoczęcia'.encode('windows-1250')])

    def _eventEndDateTime(self, event_details):
        return self._convertDateTime(event_details[u'Data zakończenia'.encode('windows-1250')],
                                     event_details[u'Czas zakończenia'.encode('windows-1250')])

    def _eventLocation(self, event_details):
        return event_details[u'Lokalizacja'.encode('windows-1250')]

    def addScheduleEvents(self, event_names, event_details):

        for ev_name in event_names:
            ev_det = event_details[ev_name]

            event = {
                'summary': ev_name.decode('windows-1250'),

                'start': {
                    'dateTime': self._eventStartDateTime(ev_det)
                },
                'end': {
                    'dateTime': self._eventEndDateTime(ev_det)
                },
            }

            loc = self._eventLocation(ev_det)
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
            self._batch.add(self._service.events().insert(calendarId=self._calendar_id,
                                                          body=event), callback=self.eventAdded, request_id=ev_name)

    def modifyScheduleEvents(self, event_names, new_event_details):

        for ev_name in event_names:
            ev_det = new_event_details[ev_name]

            patch = {
                'start': {
                    'dateTime': self._eventStartDateTime(ev_det)
                },
                'end': {
                    'dateTime': self._eventEndDateTime(ev_det)
                },
            }

            loc = self._eventLocation(ev_det)
            if loc is not None:
                patch['location'] = loc

            self._batch.add(self._service.events().patch(calendarId=self._calendar_id,
                                                         eventId=self._event_name_to_id_dict[ev_name.decode('windows-1250')],
                                                         body=patch), callback=self.eventModified, request_id=ev_name)

    def removeScheduleEvents(self, event_names):
        #TODO usuwanie z jsona lub dawanie gdzieś idziej informacji o usunięciu
        for ev_name in event_names:

            patch = {
                'status': 'cancelled'
            }

            self._batch.add(self._service.events().patch(calendarId=self._calendar_id,
                                                         eventId=self._event_name_to_id_dict[ev_name.decode('windows-1250')],
                                                         body=patch), callback=self.eventModified, request_id=ev_name)

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
            'role': 'group'
        }

        created_rule = self._service.acl().insert(calendarId=self._calendar_id, body=rule).execute()
        return created_rule['id']

    def shareCalendarWithOwner(self, email):
        rule = {
            'scope': {
                'type': 'user',
                'value': email,
            },
            'role': 'owner'
        }
        created_rule = self._service.acl().insert(calendarId=self._calendar_id, body=rule).execute()
        return created_rule['id']

    def deletePrivilege(self, acl_id):
        self._service.acl().delete(calendarId=self._calendar_id, ruleId=acl_id).execute()

    def clearCalendar(self):
        pass

    def end(self):
        json_file = open(self._event_json_path, mode='w')
        json_file.write(json.dumps(self._event_name_to_id_dict, encoding='windows-1250'))
        json_file.close()