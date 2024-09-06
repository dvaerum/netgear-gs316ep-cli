from hashlib import md5
from pathlib import Path
from time import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .misc import bad_request


class Client(requests.Session):
    def __init__(self, host: str, port: int = 80, proxy_url: str = None, *args, **kwargs):
        # noinspection PyArgumentList
        super(Client, self).__init__(*args, **kwargs)

        self.prefix_url = f"http://{host}:{port}"
        self._token = None
        self._password = None
        self._token_file_path = Path(f"/tmp/.netgear-gs316ep_token/{host}/token")

        if proxy_url is not None:
            proxies = {
                'http': proxy_url,
                'https': proxy_url,
            }
            self.proxies.update(proxies)

    def request(self, method, url, *args, **kwargs):
        url = urljoin(self.prefix_url, url)

        if self._token:
            if method == "POST" and kwargs.get('data'):
                kwargs['data']['Gambit'] = self._token

            if kwargs.get('params') is None:
                kwargs['params'] = {}
            kwargs['params']['Gambit'] = self._token

        # if method == "GET":
        # else:
        #     if self._token:
        #         if kwargs.get('data') is None:
        #             kwargs['data'] = {}
        #         kwargs['data']['Gambit'] = self._token

        return super(Client, self).request(
            method, url, *args, **kwargs
        )

    def login(self, password: str = None):
        if password is None:
            if self._password is None:
                raise Exception("The client have not been provided with a password, "
                                "it have to be provided one at least ones")
            password = self._password

        if self._token_file_path.is_file() and int(self._token_file_path.stat().st_mtime) > time() - (15 * 60):
            self._token = self._token_file_path.read_text()
            return

        resp_login_page = self.get("/", allow_redirects=False, timeout=10)

        if resp_login_page.status_code != 200:
            bad_request(resp_login_page)

        bs = BeautifulSoup(resp_login_page.text, 'html.parser')
        random_number = bs.find(name="input", id="rand").get("value")
        salted_password = _merge(password, random_number)
        hashed_password = md5(salted_password.encode()).hexdigest()

        resp_login = self.post(
            "/redirect.html", allow_redirects=False,
            data={"LoginPassword": hashed_password},
            timeout=10,
        )

        if resp_login.status_code != 200:
            bad_request(resp_login)

        bs2 = BeautifulSoup(resp_login.text, 'html.parser')
        body_onload = bs2.find("body").get("onload")
        if body_onload != 'loadHomePage()':
            login_page_error_msg = bs2.find('span', id="loginPageErrorMsg")
            if login_page_error_msg.contents:
                raise Exception(f"Login Failed - {login_page_error_msg.contents[0]}")
            else:
                raise Exception("Wrong Password")

        token = bs2.find('input', attrs={'name': "Gambit"})['value']
        self.set_token(token=token)
        self._password = password

    def set_token(self, token: str):
        self._token = token
        self._token_file_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._token_file_path.write_text(token)

    def get_token(self) -> str:
        if self._token is None:
            raise Exception("The client does not have a token,"
                            "the client needs to login successfully at least ones to obtain a token")
        return self._token

    def valid_token(self) -> bool:
        resp = self.get('/homepage.html')
        if resp.status_code != 200 or resp.text.__len__() < 250:
            return False

        return True


def _merge(password: str, random_number: str):
    arr1 = list(password)
    arr2 = list(random_number)
    result = ""
    index1 = 0
    index2 = 0
    while index1 < arr1.__len__() or index2 < arr2.__len__():
        if index1 < arr1.__len__():
            result += arr1[index1]
            index1 += 1

        if index2 < arr2.__len__():
            result += arr2[index2]
            index2 += 1

    return result
