from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, field_validator


InterfaceRole = Literal["wan", "lan", "unused", "skip"]


class RouterInfo(BaseModel):
    major: int = 7
    full: str = ""
    board: str = ""
    ram_mb: int = 0
    cpu: str = ""
    identity: str = ""


class InterfaceInfo(BaseModel):
    name: str
    type: str = "unknown"
    mac: str = ""
    running: bool = False
    disabled: bool = False
    comment: str = ""

    @property
    def is_physical(self) -> bool:
        return self.type in {"ether", "sfp", "wlan", "lte"}


class PPPoEConfig(BaseModel):
    enabled: bool = False
    wan_iface: str | None = None
    username: str = ""
    password: str = ""
    service_name: str = ""


class InterfaceAssignment(BaseModel):
    name: str
    role: InterfaceRole = "skip"
    locked: bool = False


class FirewallRules(BaseModel):
    input_established_related: bool = True
    input_drop_invalid: bool = True
    input_allow_icmp: bool = True
    input_allow_internal_management: bool = True
    input_drop_wan_admin: bool = True
    input_port_scan_guard: bool = False
    input_bruteforce_guard: bool = False
    forward_established_related: bool = True
    forward_drop_invalid: bool = True
    forward_allow_internal_to_wan: bool = True
    forward_allow_dstnat: bool = True
    forward_isolate_vlans: bool = False
    forward_drop_new_wan: bool = True
    output_established_related: bool = False
    output_drop_invalid: bool = False
    nat_masquerade: bool = True
    raw_block_dns_wan: bool = False
    log_wan_drops: bool = False


class FirewallConfig(BaseModel):
    preset: Literal["basic", "recommended", "advanced"] = "recommended"
    rules: FirewallRules = Field(default_factory=FirewallRules)


class BridgeConfig(BaseModel):
    name: str = "bridge-lan"
    protocol: Literal["rstp", "stp", "none"] = "rstp"
    vlan_filtering: bool = True


class VLANConfig(BaseModel):
    vlan_id: int
    name: str
    tagged_ports: list[str] = Field(default_factory=list)
    untagged_ports: list[str] = Field(default_factory=list)

    @field_validator("vlan_id")
    @classmethod
    def validate_vlan_id(cls, value: int) -> int:
        if not 1 <= value <= 4094:
            raise ValueError("VLAN ID must be between 1 and 4094.")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("VLAN name is required.")
        return cleaned

    @property
    def interface_name(self) -> str:
        slug = self.name.lower().replace(" ", "-")
        return f"vlan{self.vlan_id}-{slug}"


def default_firewall_config() -> FirewallConfig:
    return FirewallConfig()


@dataclass
class AppState:
    host: str = "192.168.88.1"
    port: int = 8728
    username: str = "admin"
    password: str = ""
    router_info: RouterInfo | None = None
    interfaces: list[InterfaceInfo] = field(default_factory=list)
    pppoe: PPPoEConfig = field(default_factory=PPPoEConfig)
    interface_assignments: dict[str, InterfaceAssignment] = field(default_factory=dict)
    firewall: FirewallConfig = field(default_factory=default_firewall_config)
    bridge: BridgeConfig = field(default_factory=BridgeConfig)
    vlans: list[VLANConfig] = field(default_factory=list)
    generated_script: str = ""
    last_apply_log: list[str] = field(default_factory=list)
    last_error: str | None = None

    def sync_interface_assignments(self) -> None:
        existing_names = {interface.name for interface in self.interfaces}
        self.interface_assignments = {
            name: assignment
            for name, assignment in self.interface_assignments.items()
            if name in existing_names
        }

        for interface in self.interfaces:
            if interface.name not in self.interface_assignments:
                default_role: InterfaceRole = "lan" if interface.is_physical else "skip"
                self.interface_assignments[interface.name] = InterfaceAssignment(
                    name=interface.name,
                    role=default_role,
                )

    def get_wan_interface(self) -> str | None:
        if self.pppoe.enabled and self.pppoe.wan_iface:
            return self.pppoe.wan_iface

        for assignment in self.interface_assignments.values():
            if assignment.role == "wan":
                return assignment.name
        return None

    def get_lan_interfaces(self) -> list[str]:
        return [
            assignment.name
            for assignment in self.interface_assignments.values()
            if assignment.role == "lan"
        ]

    def ensure_pppoe_wan_lock(self) -> None:
        if not self.pppoe.enabled or not self.pppoe.wan_iface:
            for assignment in self.interface_assignments.values():
                assignment.locked = False
            return

        self.sync_interface_assignments()
        for assignment in self.interface_assignments.values():
            assignment.locked = assignment.name == self.pppoe.wan_iface
            if assignment.locked:
                assignment.role = "wan"
