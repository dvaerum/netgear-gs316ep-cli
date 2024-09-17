from pprint import pprint

from .helper_functions import _get_vlans_from_html_code
from .structs import TYPE_VLANS, AccessVLAN
from ..client import Client


def get_vlans(client: Client) -> TYPE_VLANS:
    resp = client.get("/iss/specific/vlan.html")
    vlans = _get_vlans_from_html_code(resp.text)
    return vlans


def get_vlan_info(client: Client) -> str:
    ports = get_vlans(client)

    table = {}
    for vlan_id, vlan_obj in ports.items():
        for port_no, access in vlan_obj.ports_access.items():
            table.setdefault(port_no, {AccessVLAN.untagged: 1, AccessVLAN.tagged: []})

            if access == AccessVLAN.untagged:
                table[port_no][AccessVLAN.untagged] = vlan_id
            elif access == AccessVLAN.tagged:
                table[port_no][AccessVLAN.tagged].append(f"{vlan_id:>4}")

    pprint(table)

    result = "Port No | VLAN Untagged | VLAN Tagged\n"
    result += "--------|---------------|-------------\n"
    for port_no in sorted(table.keys()):
        _vlans = table[port_no]

        result += "{port:>7} | {untagged:>13} | {tagged}\n".format(
            port=port_no,
            untagged=_vlans[AccessVLAN.untagged],
            tagged=" ".join(_vlans[AccessVLAN.tagged]),
        )

    return result


def get_vlan_command(client: Client) -> str:
    resp = client.get("/iss/specific/vlan.html")
    vlans = _get_vlans_from_html_code(resp.text)

    result = "--set "
    for vlan_id in sorted(vlans.keys()):
        _vlan_obj = vlans[vlan_id]

        tmp_result = []
        for port_no, access in _vlan_obj.ports_access.items():
            if access == AccessVLAN.excluded:
                continue
            tmp_result.append(f"{port_no}:{access.name}")

        result += f"{vlan_id}:{_vlan_obj.name}@" + ",".join(tmp_result) + " "

    return result
