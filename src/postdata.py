#!/usr/bin/env python3
from functools import partial
import requests
import requests.utils
import pickle
from pathlib import Path

class GetInfo:
    def __init__(self, username, userid):
        self.userid = userid
        self.username = username
        self.session_file = Path(f"~/.config/instman/{self.username}.session").expanduser()
        self.session = None

    def create_session(self):
        """ Get creation date and username changes """
        session = requests.Session()
        with open(self.session_file, 'rb') as sessionfile:
            session.cookies = requests.utils.dict_from_cookiejar(pickle.load(sessionfile))
        # session.headers.update()
        session.headers.update({'X-CSRFToken': session.cookies.get_dict()['csrftoken']})
        session.request = partial(session.request, timeout=self.request_timeout) # type: ignore
        self.session = session

    def create_date(self, session: requests.Session, url, params):
        response = session.post(url, params=params)
        print(response.text)
        return response
