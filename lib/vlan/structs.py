from enum import Enum
from typing import Dict, NamedTuple, List, Set

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

    def __repr__(self):
        return f"{self.name}"


class ObjVLAN(NamedTuple):
    name: str
    ports_access: Dict[int, AccessVLAN]

    def ports_access_to_str(self):
        return ''.join([
            self.ports_access.get(index, AccessVLAN.excluded).value.__str__()
            for index in switch_port_iter()
        ])

    def filter_out_access_states(self, access_states: Set[AccessVLAN]) -> "ObjVLAN":
        result = {
            port_no: access
            for port_no, access in self.ports_access.items()
            if access not in access_states
        }
        return ObjVLAN(name=self.name, ports_access=result)

class MapPort2UntaggedVLAN(NamedTuple):
    select_vlan_id: int
    vlan_ids: List[int]


TYPE_VLANS = Dict[int, ObjVLAN]
