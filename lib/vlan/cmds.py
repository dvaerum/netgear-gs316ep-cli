import argparse

from .get_vlans import get_vlan_info, get_vlan_command
from .helper_functions import _parse_vlan_arguments
from ..client import Client
from .structs import ModeVLAN
from .set_vlans import set_vlans
from .set_mode import set_vlan_mode


def sub_cmd_vlan(client: Client, args: argparse.Namespace):
    if args.vlan_mode:
        set_vlan_mode(client, ModeVLAN(args.mode))

    if args.vlan_set:
        vlans = _parse_vlan_arguments(args.vlan_set)
        result = set_vlans(client=client, vlans=vlans)
        print(result)

    if args.vlan_get == "info":
        result = get_vlan_info(client)
        print(result)
    elif args.vlan_get == "command":
        result = get_vlan_command(client)
        print(result)
