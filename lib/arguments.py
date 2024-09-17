import argparse

from .firmware import sub_cmd_update
from .misc import switch_port_iter
from .vlan import ModeVLAN, sub_cmd_vlan
from .poe import sub_cmd_poe
from .mirror_port import sub_cmd_mirror_port
from os import environ

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="Netgear Switch (GS316EP) Manager")

    parser.add_argument("--host", dest="host", type=str, required=True,
                        default=environ.get("SWITCH_HOST"),
                        help="The IP or DNS address of the Switch")
    parser.add_argument("--port", dest="port", type=int, required=False,
                        default=int(environ.get("SWITCH_PORT", "80")),
                        help="The port for the Website on the Switch")
    parser.add_argument("--password", dest="password", type=str, required=True,
                        default=environ.get("SWITCH_PASSWORD"),
                        help="The password for the Switch")
    parser.add_argument("--proxy-url", dest="proxy_url", type=str, required=False,
                        default=environ.get("SWITCH_PROXY_URL"),
                        help="Enter proxy url if needed. Support for Socks5 and HTTP proxy")

    sub_command = parser.add_subparsers(title="commands", help="Select Sub-command", required=True)

    parser_update = sub_command.add_parser('update', help="Update to the latest firmware")
    parser_update.set_defaults(func=sub_cmd_update)


    parser_vlan = sub_command.add_parser('vlan', help="Config VLANs")
    parser_vlan_group = parser_vlan.add_mutually_exclusive_group(required=True)
    parser_vlan_group.add_argument('--mode',
        dest="vlan_mode", type=str, required=False,
        default=None, choices=list(ModeVLAN.__members__),
        help="Set the mode of the switch")
    parser_vlan_group.add_argument("--set",
        dest="vlan_set", type=str, required=False,
        default=None, nargs="+",
        help="Defined the vlan config. The format is: "
             "<VLAN_ID>:<VLAN_NAME>@<PORT_NO>:<tagged|untagged|excluded>,[<PORT_NO>:<tagged|untagged|excluded>] "
             "[<VLAN_ID>:<VLAN_NAME>@<PORT_NO>:<tagged|untagged|excluded>[,<PORT_NO>:<tagged|untagged|excluded>]]")
    parser_vlan_group.add_argument("--get",
        dest="vlan_get", type=str, required=False,
        default="info", choices=["info", "command"],
        help="Get VLAN config from the switch as info or a command line argument")
    parser_vlan.set_defaults(func=sub_cmd_vlan)


    parser_poe = sub_command.add_parser('poe', help="Configure PoE")
    parser_poe.add_argument("--power-cycle-ports", "--reset",
                            dest="power_cycle_ports", type=int, required=False, default=[],
                            nargs="+", choices=list(switch_port_iter(include_port_16=False)),
                            help="List the port(s) to power cycle")
    parser_poe.set_defaults(func=sub_cmd_poe)


    parser_poe = sub_command.add_parser('mirror-port', help="Configure PoE")
    parser_poe.add_argument("--disable",
                            dest="mirror_port_disable", action="store_true", required=False, default=False,
                            help="Disable port mirroring")
    parser_poe.add_argument("--src-ports",
                            dest="mirror_port_src_ports", type=int, required=False, default=[],
                            nargs="+", choices=list(switch_port_iter()),
                            help="List the port(s) to mirror")
    parser_poe.add_argument("--dest-port",
                            dest="mirror_port_dest_port", type=int, required=False, default=None,
                            choices=list(switch_port_iter()),
                            help="The port to mirror to")
    parser_poe.set_defaults(func=sub_cmd_mirror_port)


    return parser.parse_args()


