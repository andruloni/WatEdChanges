import os
import sys
from DictDiffer import DictDiffer
from WatEdApi import WatEdApi
import configparser
import csv


def getGroupCalendarDictFromFile(path):

    file = csv.DictReader(open(path, encoding='utf-8'))

    ret_dict = {}
    for row in file:
        tmp = dict(row)
        del tmp['Temat']
        ret_dict[row['Temat']] = tmp

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
        file = open(file_path, mode='w', encoding='utf-8')
        file.write(wat_api.csv_string)
        file.close()

