from enum import Enum
from typing import Dict, NamedTuple, List

from ..misc import switch_port_iter


class ModeVLAN(str, Enum):
    no_vlans = 'noVlan'
    basic_port_based_vlan = "bscPotBsd"
    advanced_port_based_vlan = "advPotBsd"
    basic_802_1q_vlan = "bsc8021Q"
    advanced_802_1q_vlan = "adv8021Q"


class AccessVLAN(int, Enum):
    tagged = 1
    untagged = 2
    excluded = 3


class ObjVLAN(NamedTuple):
    name: str
    ports_access: Dict[int, AccessVLAN]

    def ports_access_to_str(self):
        return ''.join([
            self.ports_access.get(index, AccessVLAN.excluded).value.__str__()
            for index in switch_port_iter()
        ])

class MapPort2UntaggedVLAN(NamedTuple):
    select_vlan_id: int
    vlan_ids: List[int]


TYPE_VLANS = Dict[int, ObjVLAN]
