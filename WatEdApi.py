# -*- coding: utf-8 -*-
import StringIO
import requests
import csv
from bs4 import BeautifulSoup
import time
from requests.packages.urllib3.exceptions import ConnectionError


class WatEdApi:
    url = 'https://s1.wcy.wat.edu.pl/ed/'

    headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:33.0) Gecko/20100101 Firefox/33.0',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
                'Connection': 'keep-alive',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}

    def __init__(self, login, password):
        self.user_login = login
        self.user_password = password
        self.session_string = ''

    def _downloadFile(self, download_url):
        resp = None

        """ nasz ed jest tak genialny ze trzeba odczekac jakis czas od zalogowania zanim wysle sie request o export,
            dostaniemy niby 302 a potem z redirectu 200 ale contetnt-lenght = 0 czyli bez pliku #takbardzojanuszowate #2wieczorydebugowania"""
        time.sleep(5)

        for x in range(0, 10):
            try:
                resp = requests.get(download_url, verify=False, headers=self.headers)
            except ConnectionError as e:
                raise e

            if len(resp.content) > 0:
                break

            # odstep miedzy requestami. Moze ed jest kobieta i nie jest jeszcze "gotowy" :P
            time.sleep(5)

        self.csv_string = resp.content

        if len(self.csv_string) == 0 or not self.csv_string.startswith('Temat'):
            raise ConnectionError('Cannot download schedule')

        if resp.ok:
            return StringIO.StringIO(self.csv_string)
        else:
            return None

    def getGroupCalendarFile(self, group_id, group_symbol):

        if self.logged is False:
            self.connect()

        # nie uzywane bezposrednio bo ed wymaga odpowiedniej kolejnosci argumentow #januszeprogamowania
        param_data = {
            'sid': self.session_string,
            'mid': '328',  # przeslane w wstawce <script> w logged_inc.php moze zwiazane z userem
            'iid': group_id,  # przeslane w wstawce <script> powiazane z grupa dla I2A3S1 -> 20144
            'vrf': '',  # weryfikacja WTF :P sklejka dwoch poprzednich ( mid, iid)
            'rdo': '1',
            'pos': '0',  # prawdopodbnie pozycja do autoprzeskrolowania czy cos takiego
            'exv': group_symbol,
            'opr': 'DTXT'  # typ operacji - pobranie csv
        }
        param_data['vrf'] = param_data['mid'] + param_data['iid']

        tmp_url = '%slogged.php?sid=%s&mid=%s&iid=%s&vrf=%s&rdo=%s&pos=%s&exv=%s&opr=%s' % (self.url,
                                                                                            param_data['sid'],
                                                                                            param_data['mid'],
                                                                                            param_data['iid'],
                                                                                            param_data['vrf'],
                                                                                            param_data['rdo'],
                                                                                            param_data['pos'],
                                                                                            param_data['exv'],
                                                                                            param_data['opr'], )

        file = self._downloadFile(tmp_url)
        self.csv_file = file

        return file

    def getGroupCalendarDict(self, group_id, group_symbol):

        dict_reder = self.getGroupCalendar(group_id, group_symbol)

        ret_dict = {}
        for row in dict_reder:
            tmp = dict(row)
            del tmp['Temat']
            ret_dict[row['Temat']] = tmp

        return ret_dict

    def getGroupCalendar(self, group_id, group_symbol):
        file = self.getGroupCalendarFile(group_id, group_symbol)
        dict_reader = csv.DictReader(file)
        return dict_reader

    def _login(self, post_url):
        post_data_dict = {
            'formname': 'login',
            'userid': self.user_login,
            'password': self.user_password
        }

        try:
            resp = requests.post(post_url, data=post_data_dict, verify=False, headers=self.headers)
        except ConnectionError as e:
            raise e

        if len(resp.history) > 0:
            self.logged = True
        elif len(resp.history) == 0:  # TODO change login verification method
            raise ConnectionError('Wrong Login/Password')
        else:
            raise ConnectionError("Can't login")

    def connect(self):

        try:
            resp = requests.get(self.url, verify=False, headers=self.headers)
        except ConnectionError as e:
            raise e

        soup = BeautifulSoup(resp.content)
        post_url = soup.form['action']
        self.session_string = post_url.split("=", 1)[1]
        self._login(self.url + post_url)



