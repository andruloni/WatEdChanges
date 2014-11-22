#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from DictDiffer import DictDiffer
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

if __name__ == "__main__":

    config = configparser.ConfigParser()

    if len(sys.argv) == 2:
        config.read(sys.argv[1])
    else:
        exit(1)

    dir_path = config['ed']['dir_path']
    group_id = config['ed']['group_id']
    group_symbol = config['ed']['group_symbol']
    login = config['ed']['login']
    password = config['ed']['password']

    file_path = '%s/%s_%s.csv' % (dir_path, group_id, group_symbol)

    wat_api = WatEdApi(login, password, debug=False)
    wat_api.connect()
    new_dict = wat_api.getGroupCalendarDict(group_id=group_id, group_symbol=group_symbol)

    if os.path.exists(file_path):
        old_dict = getGroupCalendarDictFromFile(file_path)

        dict_diff = DictDiffer(new_dict, old_dict)

        to_add = dict_diff.added()
        to_modify = dict_diff.changed()
        to_remove = dict_diff.removed()

    else:
        schedule_file = open(file_path, mode='w')
        schedule_file.write(wat_api.csv_string)
        schedule_file.close()

