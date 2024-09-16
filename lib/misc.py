from typing import List

import requests


def bad_request(resp: requests.Response, msg: str = None, err = None):
    if msg is None:
        msg = "Bad Request"
    if err:
        msg += f" - err: {err}"
    raise Exception(f"{msg} - Code: {resp.status_code} - body:\n{resp.text}")

def switch_port_iter(include_port_16: bool = True):
    if include_port_16:
        return range(1, 17)
    else:
        return range(1, 16)

def convert_list_of_ports_to_str(ports: List[int], include_port_16: bool = True) -> str:
    ports_str = "".join([
        "1" if port in ports else "0"
        for port in list(switch_port_iter(include_port_16=include_port_16))
    ])
    return ports_str
