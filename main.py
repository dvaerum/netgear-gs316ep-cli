import argparse

from lib import get_args, Client


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
