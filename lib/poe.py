import argparse
from typing import List

from .client import Client


def sub_cmd_poe(client: Client, _args: argparse.Namespace):
    if _args.power_cycle_ports:
        power_cycle_ports(client=client, ports=_args.power_cycle_ports)
        print("Power cycled the ports: ", _args.power_cycle_ports)
        exit(0)


def power_cycle_ports(client: Client, ports: List[int]):
    poe_port = "".join([
        "1" if port in ports else "0"
        for port in list(range(1,16))
    ])

    resp = client.post("/iss/specific/poePortConf.html", data={
        "TYPE": "resetPoe",
        "PoePort": poe_port,
    })
    if resp.text != "SUCCESS":
        raise Exception(f"Failed to power cycle ports: {ports} - html_text: {resp.text}")
