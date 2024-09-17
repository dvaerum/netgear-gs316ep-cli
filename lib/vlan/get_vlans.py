from pprint import pprint

from .helper_functions import _get_vlans_from_html_code
from .structs import TYPE_VLANS, AccessVLAN
from ..client import Client


def get_vlans(client: Client) -> TYPE_VLANS:
    resp = client.get("/iss/specific/vlan.html")
    vlans = _get_vlans_from_html_code(resp.text)
    return vlans
