import pprint
import re

from .get_vlans import get_vlans
from .helper_functions import (
    _get_vlans_from_html_code,
    _validate_vlans,
    _get_port_2_vlan_mapping,
    _get_port_2_vlan_mapping_from_html_code,
    _set_untagged_vlan_2_port,
)
from .set_mode import set_vlan_mode
from .structs import TYPE_VLANS, ModeVLAN, AccessVLAN, ObjVLAN
from ..client import Client
from ..misc import switch_port_iter, bad_request


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
            remove_vlan(client=client, vlan_id=vlan_id)
            status_code = 1

    result["status_code"] = status_code
    result["status"] = "Updated VLANs on the switch"
    result["old_vlans"] = {vlan_id: vlan_obj.filter_out_access_states({AccessVLAN.excluded}) for vlan_id, vlan_obj in current_vlans.items()}
    result["new_vlans"] = {vlan_id: vlan_obj.filter_out_access_states({AccessVLAN.excluded}) for vlan_id, vlan_obj in new_vlans.items()}
    return pprint.pformat(result, indent=4)


def remove_vlan(client: Client, vlan_id):
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
