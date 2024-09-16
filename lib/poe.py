import argparse
from typing import List

from .client import Client
from .misc import convert_list_of_ports_to_str


def sub_cmd_poe(client: Client, _args: argparse.Namespace):
    if _args.power_cycle_ports:
        power_cycle_ports(client=client, ports=_args.power_cycle_ports)
        print("Power cycled the ports: ", _args.power_cycle_ports)
        exit(0)


def power_cycle_ports(client: Client, ports: List[int]):
    poe_port = convert_list_of_ports_to_str(ports, include_port_16=False)

    resp = client.post("/iss/specific/poePortConf.html", data={
        "TYPE": "resetPoe",
        "PoePort": poe_port,
    })
    if resp.text != "SUCCESS":
        raise Exception(f"Failed to power cycle ports: {ports} - html_text: {resp.text}")
