from typing import Dict, List

from bs4 import BeautifulSoup, Tag

from .structs import TYPE_VLANS, AccessVLAN, ObjVLAN, MapPort2UntaggedVLAN
from ..client import Client
from ..misc import bad_request


def _parse_vlan_arguments(args_set: List[str]) -> TYPE_VLANS:
    vlans = {}
    for vlan_raw in args_set:
        tmp_at_split = vlan_raw.split("@")
        if tmp_at_split.__len__() != 2:
            raise Exception(f"There can only be one @ (at-symbol) in a vlan declaration - Debug: {tmp_at_split}")
        vlan_info, port_info = tmp_at_split

        tmp_vlan_info_split = vlan_info.split(":")
        if tmp_vlan_info_split.__len__() == 0:
            raise Exception("No vlan id found")

        try:
            vlan_id = int(tmp_vlan_info_split[0])
        except Exception:
            raise Exception(f"VLAN ID have to be a number and not: {tmp_vlan_info_split[0]}")

        if tmp_vlan_info_split.__len__() == 1:
            vlan_name = f"vlan{vlan_id}"
        else:
            vlan_name = ":".join(tmp_vlan_info_split[1:])

        ports_access = {}
        ports_raw = port_info.split(",")
        for port_raw in ports_raw:
            tmp_port_raw_split = port_raw.split(":")
            if tmp_port_raw_split.__len__() != 2:
                raise Exception("There can only be one : (colon) when specifying port and"
                                "if it is tagged(1), untagged(2) or excluded(3)")

            try:
                port_no = int(tmp_port_raw_split[0])
            except Exception:
                raise Exception(f"The port_no have to be a number and not: {tmp_port_raw_split[0]}")

            if tmp_port_raw_split[1].lower() in AccessVLAN.__members__.keys():
                access = AccessVLAN[tmp_port_raw_split[1]]
            else:
                try:
                    access = AccessVLAN(int(tmp_port_raw_split[1]))
                except Exception:
                    raise Exception(f"There are 3 options tagged(1), untagged(2) or excluded(3) and "
                                    f"not {tmp_port_raw_split[1]}")

            ports_access[port_no] = access
        vlans[vlan_id] = ObjVLAN(name=vlan_name, ports_access=ports_access)
    return vlans


def _get_port_2_vlan_mapping_from_html_code(html: str):
    bs = BeautifulSoup(html, 'html.parser')
    vlan_table_elem: Tag = bs.find('ul', id="pvidList")

    map_port2vlan: Dict[int, MapPort2UntaggedVLAN] = {}

    for elem in vlan_table_elem.children:
        if type(elem) != Tag:
            continue

        elem: Tag

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

        elem: Tag

        vlan_id_str = elem.find('span', attrs={"list-vid": 4}).get_text()
        vlan_id_int = int(vlan_id_str)
        vlan_name = elem.find('span', attrs={"list-vnm": 4}).get_text()

        vlan_ports_str = elem.find('input', attrs={"list-vhidmem": 4}).get("value")
        vlan_ports = {index+1: AccessVLAN(int(status))
                     for index, status in enumerate(list(vlan_ports_str))}

        vlans[vlan_id_int] = ObjVLAN(name=vlan_name, ports_access=vlan_ports)

    return vlans
