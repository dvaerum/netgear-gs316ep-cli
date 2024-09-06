import re
from enum import Enum
from typing import Dict, NamedTuple, List, Any

import requests
from bs4 import BeautifulSoup, Tag

from .client import Client
from .misc import bad_request, switch_port_iter


class ModeVLAN(str, Enum):
    no_vlans = 'noVlan'
    basic_port_based_vlan = "bscPotBsd"
    advanced_port_based_vlan = "advPotBsd"
    basic_802_1q_vlan = "bsc8021Q"
    advanced_802_1q_vlan = "adv8021Q"


class AccessVLAN(int, Enum):
    tagged = 1
    untagged = 2
    excluded = 3


class ObjVLAN(NamedTuple):
    name: str
    ports_access: Dict[int, AccessVLAN]

    def ports_access_to_str(self):
        return ''.join([
            self.ports_access.get(index, AccessVLAN.excluded).value.__str__()
            for index in switch_port_iter()
        ])

class MapPort2UntaggedVLAN(NamedTuple):
    select_vlan_id: int
    vlan_ids: List[int]


TYPE_VLANS = Dict[int, ObjVLAN]


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

    return {
        "status_code": 0, "status": f"The mode is already: {mode.value}",
        "old_mode": current_vlan_mode, "new_mode": new_vlan_mode,
    }


def _validate_vlans(vlans: TYPE_VLANS) -> TYPE_VLANS:
    vlan_names = {}
    untagged_ports = {}
    new_vlans = {}

    for id_, obj in vlans.items():
        if not 0 < id_ < 4096:
            raise Exception(f"The VLANs cannot have an ID smaller then 1 or "
                            f"bigger when 4095, but the given the ID was: {id_}")

        if type(obj) == dict:
            if set(obj.keys()) != {"name", "ports_access"}:
                raise Exception(
                    f"The VLAN object have to contain the 2 keys `name` and `ports_access`, "
                    f"but the object for VLAN ID `{id_}` doesn't: {obj}"
                )
            else:
                name = obj.get("name")
                ports_access = obj.get("ports_access")
        else:
            name = obj.name
            ports_access = obj.ports_access

        if type(name) != str:
            raise Exception(f"The attribute `name` of the VLAN object have to be a string, "
                            f"but the one with VLAN ID `{id_}` has the type `{type(name)}`")

        if name.__len__() > 20:
            raise Exception(f"The attribute `name` of the VLAN object cannot have a string longer then 20 characters, "
                            f"but the one with VLAN ID `{id_}` has the name `{name}` "
                            f"which is `{name.__len__()}` characters long")

        if name in vlan_names.keys():
            raise Exception(f"There cannot be 2 VLANs with the same name! "
                            f"The VLAN ID `{id_}` has the same name (`{name}`) as the VLAN ID `{vlan_names[name]}`.")
        else:
            vlan_names[name] = id_

        if type(ports_access) != dict:
            raise Exception(f"The attribute `ports_access` of the VLAN object have to be a dictionary, "
                            f"but the one with VLAN ID `{id_}` has the type `{type(name)}`")

        new_ports_access = {}
        for port_no, access in ports_access.items():
            if type(port_no) != int:
                raise Exception(
                    f"The port numbers, which are provided as the key in the dictionary "
                    f"for the attribute `ports_access` of the VLAN object, have to be an integer. "
                    f"However, that is not the case for the VLAN ID `{id_}`."
                )

            if not 1 <= port_no <= 16:
                raise Exception(
                    f"The port numbers, which are provided as the key in the dictionary "
                    f"for the attribute `ports_access` of the VLAN object, "
                    f"have to be an number which between 1-16, not `{port_no}`. "
                    f"However, that is not the case for the VLAN ID `{id_}`."
                )

            if type(access) == AccessVLAN:
                new_access = access

            elif type(access) == int:
                if 1 <= access <= 3:
                    new_access = AccessVLAN(access)
                else:
                    raise Exception(
                        f"The port_access type, which are provided as the value in the dictionary "
                        f"for the attribute `ports_access` of the VLAN object, "
                        f"have to be an number which between 1-3, not `{port_no}`. "
                        f"Note: `1 = tagged`, `2 = untagged` and `3 = excluded`. "
                        f"However, that is not the case for port `{port_no}` for the VLAN ID `{id_}`."
                    )
            elif type(access) == str:
                if access in {"tagged", "untagged", "excluded"}:
                    new_access = AccessVLAN[access]
                else:
                    raise Exception(
                        f"The port_access type, which are provided as the value in the dictionary "
                        f"for the attribute `ports_access` of the VLAN object, "
                        f"have to be an of the following `tagged`, `untagged` or `excluded`. "
                        f"However, that is not the case for port `{port_no}` for the VLAN ID `{id_}`."
                    )
            else:
                raise Exception(
                    f'The port_access type, which are provided as the value in the dictionary '
                    f'for the attribute `ports_access` of the VLAN object, '
                    f'can one of 3 types `{AccessVLAN.__class__.name}`, `integer` or `str`, not `{type(access)}`. '
                    f'Note: `1 = "tagged"`, `2 = "untagged"` and `3 = "excluded"`. '
                    f'However, that is not the case for port `{port_no}` for the VLAN ID `{id_}`.'
                )

            if new_access == AccessVLAN.untagged:
                if port_no in untagged_ports.keys():
                    raise Exception(
                        f"There cannot be 2 VLANs which are untagged on the same port! "
                        f"The VLAN ID `{id_}` is untagged on the same port (`{port_no}`) "
                        f"as the VLAN ID `{untagged_ports[port_no]}`."
                    )
                else:
                    untagged_ports[port_no] = id_

            new_ports_access[port_no] = new_access

        new_vlans[id_] = ObjVLAN(name=name, ports_access=new_ports_access)

    return new_vlans


def _get_vlans_from_html_code(html: str):
    bs = BeautifulSoup(html, 'html.parser')
    vlan_table_elem: Tag = bs.find('ul', id="AQVTbl")

    vlans: TYPE_VLANS = {}

    for elem in vlan_table_elem.children:
        if type(elem) != Tag:
            continue
        vlan_id_str = elem.find('span', attrs={"list-vid": 4}).get_text()
        vlan_id_int = int(vlan_id_str)
        vlan_name = elem.find('span', attrs={"list-vnm": 4}).get_text()

        vlan_ports_str = elem.find('input', attrs={"list-vhidmem": 4}).get("value")
        vlan_ports = {index+1: AccessVLAN(int(status))
                     for index, status in enumerate(list(vlan_ports_str))}

        vlans[vlan_id_int] = ObjVLAN(name=vlan_name, ports_access=vlan_ports)

    return vlans


def error_handler_cannot_remove_port(client: Client, html_text: str) -> bool:
    check_text = re.search(
        r"Cannot remove port [@]?(?P<PORT>[0-9]+)[@]? from this VLAN. Change its PVID first",
        html_text,
        re.IGNORECASE
    )
    if check_text is None:
        return False

    vlan_id = 1

    port_no = int(check_text.groupdict().get("PORT"))
    vlans = get_vlans(client)

    vlan_obj = vlans[vlan_id]
    vlan_obj.ports_access[port_no] = AccessVLAN.untagged

    _add_vlan(client=client, vlan_id=vlan_id, vlan_obj=vlan_obj)
    _set_untagged_vlan_2_port(client=client, port_no=port_no, vlan_id=vlan_id)

    return True


def _add_vlan(client: Client, vlan_id: int, vlan_obj: ObjVLAN) -> str:
    while True:
        resp = client.post("/iss/specific/vlan.html", data={
            "page": "adv8021QPage",
            "ACTION": "add",
            "VLAN_ID": vlan_id,
            "VLAN_NAME": vlan_obj.name,
            "hiddenMem": vlan_obj.ports_access_to_str(),
            "voiceVLANID": 0,
            "autoCameraVLANID": 0,
            "autoWifiVLANID": 0,
            "fsVoiceVlanCos": 6,
            "fsAutoCameraVlanCos": 6,
            "fsAutoWifiVlanCos": 6
        })
        html_text = resp.text

        if error_handler_cannot_remove_port(client=client, html_text=html_text) is False:
            break

    vlans = _get_vlans_from_html_code(html_text)
    if not (vlan_id in vlans and
            vlans[vlan_id].name == vlan_obj.name and
            vlans[vlan_id].ports_access_to_str() == vlan_obj.ports_access_to_str()):
        bad_request(resp)

    return resp.text


def get_vlans(client: Client) -> TYPE_VLANS:
    resp = client.get("/iss/specific/vlan.html")
    vlans = _get_vlans_from_html_code(resp.text)
    return vlans


def _get_port_2_vlan_mapping_from_html_code(html: str):
    bs = BeautifulSoup(html, 'html.parser')
    vlan_table_elem: Tag = bs.find('ul', id="pvidList")

    map_port2vlan: Dict[int, MapPort2UntaggedVLAN] = {}

    for elem in vlan_table_elem.children:
        if type(elem) != Tag:
            continue
        port_no_str = elem.find("span", attrs={"class": "port-count"}).get_text()
        port_no_int = int(port_no_str)
        vlan_ids_str: str = elem.find('span', attrs={"class": "hid-txt pvid-table-vlan-list"}).get_text()

        select_vlan_id = None
        vlan_ids = []
        for vlan_id_str in vlan_ids_str.split(","):
            vlan_id_str = vlan_id_str.strip()
            if vlan_id_str.endswith("*"):
                select_vlan_id = int(vlan_id_str[:-1])
                vlan_ids.append(select_vlan_id)
            else:
                vlan_ids.append(int(vlan_id_str))

        map_port2vlan[port_no_int] = MapPort2UntaggedVLAN(select_vlan_id=select_vlan_id, vlan_ids=vlan_ids)

    return map_port2vlan


def _get_port_2_vlan_mapping(client: Client):
    resp = client.get("/iss/specific/vlan.html")
    vlans = _get_port_2_vlan_mapping_from_html_code(resp.text)
    return vlans


def _set_untagged_vlan_2_port(client: Client, port_no: int, vlan_id: int):
    resp = client.post("/iss/specific/vlan.html", data={
        "page": "adv8021QPage",
        "ACTION": "setPvid",
        "PORT": port_no,
        "PVID": vlan_id,
    })
    result = _get_port_2_vlan_mapping_from_html_code(resp.text)
    if result[port_no].select_vlan_id != vlan_id:
        bad_request(resp)


def _remove_vlan(client: Client, vlan_id):
    resp = client.post("/iss/specific/vlan.html", data={
        "page": "adv8021QPage",
        "ACTION": "delete",
        "VLAN_ID": vlan_id,
    })

    if "You can not remove this VLAN" in resp.text:
        bad_request(resp, msg=f"Bad Request ({resp.text})")

    result = _get_vlans_from_html_code(resp.text)
    if result.get(vlan_id):
        bad_request(resp)


def set_vlans(client: Client, vlans = TYPE_VLANS):
    result = set_vlan_mode(client=client, mode=ModeVLAN.advanced_802_1q_vlan)
    status_code = 0

    new_vlans = _validate_vlans(vlans)
    current_vlans = get_vlans(client)

    new_port2vlan_mapping = {port_no: 1 for port_no in switch_port_iter()}
    new_vlan2port_mapping = {1: list(switch_port_iter())}
    for vlan_id, vlan_obj in new_vlans.items():
        for port_no, port_access in vlan_obj.ports_access.items():
            if port_access == AccessVLAN.untagged:
                new_port2vlan_mapping[port_no] = vlan_id
                new_vlan2port_mapping.setdefault(vlan_id, [])
                new_vlan2port_mapping[vlan_id].append(port_no)
                new_vlan2port_mapping[1].remove(port_no)

    new_vlans.setdefault(1, ObjVLAN(name="Default", ports_access={}))
    for port_no, vlan_id in new_port2vlan_mapping.items():
        if vlan_id == 1:
            new_vlans[1].ports_access[port_no] = AccessVLAN.untagged

    add_vlans = set(new_vlans.keys()) - set(current_vlans.keys())
    if add_vlans:
        for vlan_id in add_vlans:
            _add_vlan(client, vlan_id, new_vlans[vlan_id])
            status_code = 1

    edit_vlans = sorted(set(new_vlans.keys()) & set(current_vlans.keys()))
    if edit_vlans:
        current_port2vlan_mapping = _get_port_2_vlan_mapping(client)

        for port_no in switch_port_iter():
            curr_port2vlan = current_port2vlan_mapping[port_no]
            new_port2vlan_id = new_port2vlan_mapping[port_no]
            if curr_port2vlan.select_vlan_id != new_port2vlan_id:
                if new_port2vlan_id not in curr_port2vlan.vlan_ids:
                    tmp_vlan_obj = ObjVLAN(name=new_vlans[new_port2vlan_id].name,
                                           ports_access=new_vlans[new_port2vlan_id].ports_access.copy())
                    for _port_no in new_vlan2port_mapping[new_port2vlan_id]:
                        tmp_vlan_obj.ports_access[_port_no] = AccessVLAN.untagged

                    html = _add_vlan(client=client, vlan_id=new_port2vlan_id, vlan_obj=tmp_vlan_obj)
                    current_port2vlan_mapping = _get_port_2_vlan_mapping_from_html_code(html)

                _set_untagged_vlan_2_port(client=client, port_no=port_no, vlan_id=new_port2vlan_id)
                status_code = 1

        for vlan_id in edit_vlans:
            status_code = 1
            _add_vlan(client, vlan_id, new_vlans[vlan_id])

    remove_vlans = set(current_vlans.keys()) - set(new_vlans.keys())
    if remove_vlans:
        for vlan_id in remove_vlans:
            _remove_vlan(client=client, vlan_id=vlan_id)
            status_code = 1

    result["status_code"] = status_code
    result["status"] = "Updated VLANs on the switch"
    result["old_vlans"] = current_vlans
    result["new_vlans"] = new_vlans
    return result
