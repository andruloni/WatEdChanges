# -*- coding: utf-8 -*-
import os
import sys
from DictDiffer import DictDiffer
from GoogleCalendar import GoogleCalendar
from WatEdApi import WatEdApi
import configparser
import csv


def getGroupCalendarDictFromFile(path):
    dict_reader = csv.DictReader(open(path))

    ret_dict = {}
    for row in dict_reader:
        tmp = dict(row)

        # don't ask why...
        temat = ('Temat' if 'Temat' in tmp else '﻿Temat')
        del tmp[temat]
        ret_dict[row[temat]] = tmp

    return ret_dict


def isSomethinkTodo(changes):

    ret = False
    for key, val in changes.items():
        if len(val) > 0:
            ret = True

    return ret

if __name__ == "__main__":

    script_cfg = configparser.ConfigParser()

    if len(sys.argv) == 2:
        script_cfg.read(sys.argv[1])
    else:
        exit(1)

    ed = script_cfg['ed']
    wat_api = WatEdApi(ed['login'], ed['password'], debug=True)
    wat_api.connect()

    google = script_cfg['google']
    g_cal = GoogleCalendar(google['key_path'], google['mail'])

    emails = script_cfg['emails']

    id_cfg = configparser.ConfigParser()
    id_cfg.read(google['id_file'])

    calendars = id_cfg['calendars'] if 'calendars' in id_cfg else {}

    groups = script_cfg['groups']
    for group_symbol, group_id in groups.items():

        new_dict = wat_api.getGroupCalendarDict(group_id, group_symbol)

        file_path = '%s/%s.csv' % (ed['plan_path'], group_symbol)
        old_dict = getGroupCalendarDictFromFile(file_path) if os.path.exists(file_path) else {}

        dict_diff = DictDiffer(new_dict, old_dict)
        changes = {'to_add': dict_diff.added(), 'to_modify': dict_diff.changed(), 'to_remove': dict_diff.removed()}

        if isSomethinkTodo(changes):

            event_dict_file = '%s/%s.json' % (google['calendars_json_dir'], group_symbol)

            if group_symbol in calendars:
                g_cal.setCalendar(calendars[group_symbol], event_dict_file)
            else:  # cal adress don't exist, create new cal
                cal_id = g_cal.createCalendar(group_symbol)
                g_cal.setCalendar(cal_id, event_dict_file)

                acl_adm_id = g_cal.shareCalendarWithOwner(emails['admin_%s' % (group_symbol if 'admin_%s' % group_symbol in emails else 'default')])
                acl_grp_id = g_cal.shareCalendarWithGroup(emails[group_symbol if group_symbol in emails else 'default'])

                id_cfg.set('calendars', group_symbol, str(cal_id))
                id_cfg.set('acl', 'own_%s' % group_symbol, str(acl_adm_id))
                id_cfg.set('acl', 'grp_%s' % group_symbol, str(acl_grp_id))

                # save config
                with open(google['id_file'], 'w') as f:
                    id_cfg.write(f)

            if 'to_add' in changes:
                g_cal.addScheduleEvents(changes['to_add'], new_dict)

            if 'to_modify' in changes:
                g_cal.modifyScheduleEvents(changes['to_modify'], new_dict)

            if 'to_remove' in changes:
                if len(changes['to_remove']) < 3:
                    g_cal.removeScheduleEvents(changes['to_remove'])
                else:
                    pass #TODO add log messege

            g_cal.pushChanges()
            g_cal.end()
            schedule_file = open(file_path, mode='w')
            schedule_file.write(wat_api.csv_string)
            schedule_file.close()
