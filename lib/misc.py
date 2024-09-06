import requests


def bad_request(resp: requests.Response, msg: str = None, err = None):
    if msg is None:
        msg = "Bad Request"
    if err:
        msg += f" - err: {err}"
    raise Exception(f"{msg} - Code: {resp.status_code} - body:\n{resp.text}")


def switch_port_iter():
    return range(1, 17)
