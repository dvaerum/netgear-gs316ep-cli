import pprint
from bs4 import BeautifulSoup

from .structs import ModeVLAN
from ..client import Client
from ..misc import bad_request


def get_vlan_mode(client: Client) -> ModeVLAN:
    resp = client.get("/iss/specific/vlan.html")

    bs = BeautifulSoup(resp.text, 'html.parser')
    current_vlan_mode = bs.find("span", attrs={"class": "status-text"}).parent.get("vlanmode")
    if current_vlan_mode is None:
        bad_request(resp)

    return ModeVLAN(current_vlan_mode)


def set_vlan_mode(client: Client, mode: ModeVLAN | str):
    if type(mode) == str:
        mode = ModeVLAN(mode)

    if mode in [ModeVLAN.basic_port_based_vlan, ModeVLAN.advanced_port_based_vlan, ModeVLAN.basic_802_1q_vlan]:
        raise TypeError(f'The VLAN Mode is not supported - mode: {mode}')

    current_vlan_mode = get_vlan_mode(client)

    if current_vlan_mode == mode:
        return {
            "status_code": 0, "status": f"The mode is already: {mode.value}",
            "old_mode": current_vlan_mode, "new_mode": mode,
        }

    resp = client.post("/iss/specific/vlan.html", data={"page": "", "VLAN_MOD_SET": mode.value})
    bs = BeautifulSoup(resp.text, 'html.parser')
    try:
        new_vlan_mode_str = bs.find("span", attrs={"class": "status-text"}).parent.get("vlanmode")
    except Exception as err:
        bad_request(resp, err=err)

    new_vlan_mode = ModeVLAN(new_vlan_mode_str)
    if new_vlan_mode != mode:
        bad_request(resp)

    result = {
        "status_code": 0, "status": f"The mode is already: {mode.value}",
        "old_mode": current_vlan_mode, "new_mode": new_vlan_mode,
    }
    return pprint.pformat(result, indent=4)
