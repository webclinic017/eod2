from datetime import datetime, timedelta
from pickle import dump, load
from requests import Session
from requests.exceptions import ReadTimeout
from pathlib import Path

DIR = Path(__file__).parent


class Dates:
    def __init__(self):
        self.today = datetime.combine(datetime.today(), datetime.min.time())
        self.file = DIR / 'eod2_data' / 'lastupdate.txt'
        self.dt = self.getLastUpdated()
        self.pandas_dt = self.dt.strftime('%Y-%m-%d')

    def getLastUpdated(self):
        if not self.file.is_file():
            return self.today - timedelta(1)

        return datetime.fromisoformat(self.file.read_text().strip())

    def setLastUpdated(self):
        self.file.write_text(self.dt.isoformat())

    def getNextDate(self):
        curTime = datetime.today()
        nxtDt = self.dt + timedelta(1)

        if nxtDt > curTime:
            exit('All Up To Date')

        if nxtDt.day == curTime.day and curTime.hour < 19:
            exit("All Up To Date. Check again after 7pm for today's EOD data")

        week_day = nxtDt.weekday()

        if week_day > 4:
            self.dt = nxtDt + timedelta(7 - week_day)
        else:
            self.dt = nxtDt

        self.pandas_dt = self.dt.strftime('%Y-%m-%d')
        return


class NSE:

    def __init__(self):

        self.cookie_file = DIR / 'cookies'

        uAgent = 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'

        self.headers = {
            'User-Agent': uAgent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www1.nseindia.com'
        }

        self.session = Session()
        self.cookies = self.__getCookies()
        self.dateFmt = '%Y%m%d'

    def __setCookies(self):
        r = self.makeRequest('https://www.nseindia.com/option-chain',
                             params=None,
                             timeout=10,
                             expectJson=False)

        if not r.ok:
            exit(f'Error: set cookie. {r.status_code}: {r.reason}')

        cookies = r.cookies

        with (DIR / 'cookies').open('wb') as f:
            dump(cookies, f)

        return cookies

    def __getCookies(self):
        file = DIR / 'cookies'

        if file.is_file():
            with file.open('rb') as f:
                cookies = load(f)

            if self.__hasCookiesExpired(cookies):
                cookies = self.__setCookies()

            return cookies

        return self.__setCookies()

    @staticmethod
    def __hasCookiesExpired(cookies):
        for cookie in cookies:
            if cookie.is_expired():
                return True

        return False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.session.close()

    def exit(self):
        self.session.close()

    def download(self, url):
        fname = DIR / url.split("/")[-1]

        with self.session.get(url,
                              stream=True,
                              headers=self.headers,
                              timeout=15) as r:

            with open(fname, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1000000):
                    f.write(chunk)
        return fname

    def makeRequest(self, url, params, expectJson=True, timeout=15):
        cookies = self.cookies if hasattr(self, 'cookies') else None
        try:
            r = self.session.get(url, params=params, headers=self.headers,
                                 cookies=cookies, timeout=timeout)
        except ReadTimeout:
            exit('Request timed out')

        if not r.ok:
            exit(f'{r.status_code}: {r.reason}')

        if expectJson:
            return r.json()

        return r