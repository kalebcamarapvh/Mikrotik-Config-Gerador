from __future__ import annotations

from .connector import RouterConnection
from .models import InterfaceInfo


def infer_interface_type(raw: dict[str, object]) -> str:
    raw_type = str(raw.get("type", "")).lower()
    name = str(raw.get("name", "")).lower()

    if raw_type:
        if "ether" in raw_type:
            return "ether"
        if "wireless" in raw_type or "wifi" in raw_type or name.startswith("wlan"):
            return "wlan"
        if "sfp" in raw_type:
            return "sfp"
        if "lte" in raw_type:
            return "lte"
        if "bridge" in raw_type:
            return "bridge"
        if "vlan" in raw_type:
            return "vlan"
        if "pppoe" in raw_type:
            return "pppoe-out"

    if name.startswith("ether"):
        return "ether"
    if name.startswith("wlan"):
        return "wlan"
    if name.startswith("sfp"):
        return "sfp"
    if name.startswith("bridge"):
        return "bridge"
    if name.startswith("vlan"):
        return "vlan"
    return "unknown"


def discover_interfaces(connection: RouterConnection) -> list[InterfaceInfo]:
    rows = connection.run_command("/interface/print")
    interfaces: list[InterfaceInfo] = []

    for raw in rows:
        interfaces.append(
            InterfaceInfo(
                name=str(raw.get("name", "")),
                type=infer_interface_type(raw),
                mac=str(raw.get("mac-address", "")),
                running=_to_bool(raw.get("running", False)),
                disabled=_to_bool(raw.get("disabled", False)),
                comment=str(raw.get("comment", "")),
            )
        )

    return sorted(interfaces, key=lambda item: item.name)


def summarize_ports(interfaces: list[InterfaceInfo]) -> str:
    physical = [interface for interface in interfaces if interface.is_physical]
    if not physical:
        return "No physical ports detected"

    counts: dict[str, int] = {}
    for interface in physical:
        counts[interface.type] = counts.get(interface.type, 0) + 1

    parts = [f"{count}x {kind.upper()}" for kind, count in sorted(counts.items())]
    return ", ".join(parts)


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "yes", "1"}
