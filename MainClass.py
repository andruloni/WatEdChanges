# -*- coding: utf-8 -*-
from httplib import HTTPException
import os
from googleapiclient.errors import HttpError
from DictDiffer import DictDiffer
from GoogleCalendar import GoogleCalendar
from WatEdApi import WatEdApi
import configparser
import csv


class MainClass:

    def __init__(self, script_config_path):
        self.script_cfg = None
        self.plan_path = None
        self.login = None
        self.password = None
        self.google = None
        self.emails = None
        self.google_id_conf_path = None
        self.id_cfg = None
        self.calendars = None
        self.wat_api = None
        self.g_cal_api = None
        self._ready_to_work = False
        self.parseScriptConfig(script_config_path)
        self.parseGoogleConfig()

    def debug(self):
        import httplib
        import logging
        httplib.HTTPConnection.debuglevel = 1
        logging.basicConfig(level=logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    def getGroupCalendarDictFromFile(self, path):
        dict_reader = csv.DictReader(open(path))

        ret_dict = {}
        for row in dict_reader:
            tmp = dict(row)

            # don't ask why...
            temat = ('Temat' if 'Temat' in tmp else '﻿Temat')
            del tmp[temat]
            ret_dict[row[temat]] = tmp

        return ret_dict

    def isSomethinkTodo(self, changes):

        for key, val in changes.items():
            if len(val) > 0:
                return True

        return False

    def parseScriptConfig(self, script_config_path):
        self.script_cfg = configparser.ConfigParser()
        self.script_cfg.read(script_config_path)
        ed = self.script_cfg['ed']
        self.plan_path = ed['plan_path']
        self.login = ed['login']
        self.password = ed['password']
        self.google = self.script_cfg['google']
        self.emails = self.script_cfg['emails']

    def parseGoogleConfig(self):
        self.id_cfg = configparser.ConfigParser()
        self.id_cfg.read(self.google['id_file'])
        self.calendars = self.id_cfg['calendars'] if 'calendars' in self.id_cfg else {}

    def setUp(self):
        self.wat_api = WatEdApi(self.login, self.password)
        self.wat_api.connect()

        self.g_cal_api = GoogleCalendar(self.google['key_path'], self.google['mail'])

        self._ready_to_work = True

    def saveState(self, file_path):
        self.g_cal_api.end()
        schedule_file = open(file_path, mode='w')
        schedule_file.write(self.wat_api.csv_string)
        schedule_file.close()

    def processGroup(self, group_symbol, group_id):

        if self._ready_to_work is False:
            self.setUp()

        new_dict = self.wat_api.getGroupCalendarDict(group_id, group_symbol)

        file_path = '%s/%s.csv' % (self.plan_path, group_symbol)
        old_dict = self.getGroupCalendarDictFromFile(file_path) if os.path.exists(file_path) else {}

        dict_diff = DictDiffer(new_dict, old_dict)
        changes = {'to_add': dict_diff.added(), 'to_modify': dict_diff.changed(), 'to_remove': dict_diff.removed()}

        if self.isSomethinkTodo(changes):

            event_dict_file = '%s/%s.json' % (self.google['calendars_json_dir'], group_symbol)

            if group_symbol in self.calendars:
                self.g_cal_api.setCalendar(self.calendars[group_symbol], event_dict_file)
            else:  # cal adress don't exist, create new cal
                cal_id = None
                try:
                    cal_id = self.g_cal_api.createCalendar(group_symbol)
                    self.id_cfg.set('calendars', group_symbol, str(cal_id))
                    self.g_cal_api.setCalendar(cal_id, event_dict_file)

                    acl_adm_id = self.g_cal_api.shareCalendarWithOwner(self.emails['admin_%s' % (group_symbol if 'admin_%s' % group_symbol in self.emails else 'default')])
                    self.id_cfg.set('acl', 'own_%s' % group_symbol, str(acl_adm_id))
                    acl_grp_id = self.g_cal_api.shareCalendarWithGroup(self.emails[group_symbol if group_symbol in self.emails else 'default'])
                    self.id_cfg.set('acl', 'grp_%s' % group_symbol, str(acl_grp_id))

                    # save config
                    with open(self.google['id_file'], 'w') as f:
                        self.id_cfg.write(f)

                except (HTTPException, HttpError), e:
                    #TODO add log messege
                    if cal_id is not None:
                        self.g_cal_api.removeCalendar()

                    raise e

            if 'to_add' in changes and len(changes['to_add']) > 0:
                self.g_cal_api.addScheduleEvents(changes['to_add'], new_dict)

            if 'to_modify' in changes and len(changes['to_modify']) > 0:
                self.g_cal_api.modifyScheduleEvents(changes['to_modify'], new_dict)

            if 'to_remove' in changes and len(changes['to_remove']) > 0:
                if len(changes['to_remove']) < 3:
                    self.g_cal_api.removeScheduleEvents(changes['to_remove'])
                else:
                    pass  #TODO add log messege

            self.g_cal_api.pushChanges()
            self.saveState(file_path)

    def processAllGroups(self):

        if self._ready_to_work is False:
            self.setUp()

        groups = self.script_cfg['groups']
        for group_symbol, group_id in groups.items():
            self.processGroup(group_symbol, group_id)