import argparse

from lib.client import Client
from lib.firmware import update
from lib.vlan import set_vlan_mode, ModeVLAN, set_vlans, AccessVLAN
from lib.poe import sub_cmd_poe
from os import environ


def sub_cmd_update(client: Client, _args: argparse.Namespace):
    result = update(client)
    print(result)


def sub_cmd_vlan(client: Client, args: argparse.Namespace):
    if args.mode:
        set_vlan_mode(client, ModeVLAN(args.mode))

    if args.set:
        vlans = {}
        for vlan_raw in args.set:
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
            vlans[vlan_id] = {"name": vlan_name, "ports_access": ports_access}

        result = set_vlans(client=client, vlans=vlans)
        print(result)


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
    parser_vlan.add_argument('--mode', dest="mode", type=str, required=False,
                             default=None, choices=list(ModeVLAN.__members__),
                             help="Set the mode of the switch")
    parser_vlan.add_argument("--set", dest="set", type=str, required=False,
                             default=None, nargs="+",
                             help="Defined the vlan config. The format is: "
                                  "<VLAN_ID>:<VLAN_NAME>@"
                                  "<PORT_NO>:<tagged|untagged|excluded>,"
                                  "[<PORT_NO>:<tagged|untagged|excluded>] "
                                  "[<VLAN_ID>:<VLAN_NAME>@"
                                  "<PORT_NO>:<tagged|untagged|excluded>"
                                  "[,<PORT_NO>:<tagged|untagged|excluded>]]")
    parser_vlan.set_defaults(func=sub_cmd_vlan)


    parser_poe = sub_command.add_parser('poe', help="Configure PoE")
    parser_poe.add_argument("--power-cycle-ports", "--reset",
                            dest="power_cycle_ports", type=int, required=False, default=[],
                            nargs="+", choices=list(range(1,16)),
                            help="List the port(s) to power cycle")
    parser_poe.set_defaults(func=sub_cmd_poe)


    return parser.parse_args()


def main():
    args = get_args()

    client = Client(host=args.host, port=args.port, proxy_url=args.proxy_url)
    client.login(password=args.password)

    args.func(client, args)
    exit(0)

    # result = update(client)
    # print(result)

    # result = set_vlan_mode(client, ModeVLAN.advanced_802_1q_vlan)
    # print(result)

    # result = set_vlans(client, vlans={
    #     1000: {"name": "Zone00", "ports_access": {
    #         1: "untagged", 2: 2, 3: AccessVLAN.untagged, 4: "untagged", 15: "tagged"
    #     }},
    #     1001: {"name": "Zone01", "ports_access": {
    #         5: "untagged", 6: 2, 7: AccessVLAN.untagged, 8: "untagged", 15: "tagged"
    #     }},
    #     1002: {"name": "Zone02", "ports_access": {
    #         9: "untagged", 10: 2, 11: AccessVLAN.untagged, 12: "untagged", 15: "tagged"
    #     }},
    # })
    # print(result)


if __name__ == '__main__':
    main()
