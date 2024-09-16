import argparse
from typing import List

from .client import Client
from .misc import convert_list_of_ports_to_str


def sub_cmd_mirror_port(client: Client, _args: argparse.Namespace):
    if _args.mirror_port_disable is True:
        mirror_port_disable(client=client)
        print("Disabled port mirroring")
        exit(0)

    elif _args.mirror_port_src_ports and _args.mirror_port_dest_port:
        mirror_port(client=client, src_ports=_args.mirror_port_src_ports, dest_port=_args.mirror_port_dest_port)
        print("Mirrored the port(s) `{}` to the port `{}`".format(
            sorted(_args.mirror_port_src_ports), _args.mirror_port_dest_port,
        ))
        exit(0)

    else:
        print("Error: There have to be provided at least one source and destination port")
        exit(1)

def mirror_port_disable(client):
    resp = client.post("/iss/specific/port_monitorconfig.html", data={
        "SessionMode": "1",
        "SourcePort": "",
        "DestPort": "-1",
    })
    if resp.text != "SUCCESS":
        raise Exception(f"Failed to disable port mirroring - html_text: {resp.text}")

def mirror_port(client: Client, src_ports: List[int], dest_port: int):
    if dest_port in src_ports:
        raise Exception(f"Port `{dest_port}` can't be the destination port and the source port(s) at the same time")

    src_ports_str = convert_list_of_ports_to_str(src_ports)
    resp = client.post("/iss/specific/port_monitorconfig.html", data={
        "SessionMode": "0",
        "SourcePort": src_ports_str,
        "DestPort": f"{dest_port}",
    })
    if resp.text != "SUCCESS":
        raise Exception(f"Failed to mirror port(s) `{src_ports}` to the port `{dest_port}` - html_text: {resp.text}")
