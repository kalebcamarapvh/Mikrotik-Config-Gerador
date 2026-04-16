from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from jinja2 import Environment, FileSystemLoader

from .models import AppState


@dataclass
class RouterCommand:
    label: str
    path: str
    params: dict[str, Any]
    check_path: str | None = None
    ensure_filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandBlock:
    name: str
    commands: list[RouterCommand]


class Configurator:
    def __init__(self) -> None:
        template_root = Path(__file__).resolve().parent.parent / "templates"
        self.environment = Environment(
            loader=FileSystemLoader(str(template_root)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_script(self, state: AppState) -> str:
        version_folder = self._version_folder(state)
        context = self._context(state)
        sections: list[str] = []

        if state.pppoe.enabled and state.pppoe.wan_iface:
            sections.append(self._render(version_folder, "pppoe.rsc.j2", context))

        if state.get_lan_interfaces() or state.vlans:
            sections.append(self._render(version_folder, "bridge.rsc.j2", context))

        preset_template = f"firewall_{state.firewall.preset}.rsc.j2"
        sections.append(self._render(version_folder, preset_template, context))

        if state.vlans:
            sections.append(self._render(version_folder, "vlan.rsc.j2", context))

        script = "\n\n".join(section.strip() for section in sections if section.strip())
        state.generated_script = script
        return script

    def build_plan(self, state: AppState) -> list[CommandBlock]:
        blocks: list[CommandBlock] = []

        pppoe_commands = self._pppoe_commands(state)
        if pppoe_commands:
            blocks.append(CommandBlock(name="Configuring PPPoE client", commands=pppoe_commands))

        bridge_commands = self._bridge_commands(state)
        if bridge_commands:
            blocks.append(CommandBlock(name="Configuring bridge", commands=bridge_commands))

        firewall_commands = self._firewall_commands(state)
        if firewall_commands:
            blocks.append(CommandBlock(name="Applying firewall rules", commands=firewall_commands))

        vlan_commands = self._vlan_commands(state)
        if vlan_commands:
            blocks.append(CommandBlock(name="Configuring VLANs", commands=vlan_commands))

        return blocks

    def apply(
        self,
        state: AppState,
        connection: Any,
        progress: Callable[[str], None] | None = None,
    ) -> list[str]:
        log: list[str] = []

        for block in self.build_plan(state):
            for command in block.commands:
                try:
                    if self._exists(connection, command):
                        message = f"[=] {command.label} already exists"
                        log.append(message)
                        if progress:
                            progress(message)
                        continue

                    connection.run_command(command.path, **self._serialize_params(command.params))
                    message = f"[+] {command.label}"
                    log.append(message)
                    if progress:
                        progress(message)
                except Exception as exc:  # pragma: no cover - network dependent
                    message = f"[x] {command.label}: {exc}"
                    log.append(message)
                    if progress:
                        progress(message)

        if not log:
            message = "[i] No configuration changes were generated."
            log.append(message)
            if progress:
                progress(message)

        state.last_apply_log = log
        return log

    def _render(self, version_folder: str, template_name: str, context: dict[str, Any]) -> str:
        template = self.environment.get_template(f"{version_folder}/{template_name}")
        return template.render(**context)

    def _context(self, state: AppState) -> dict[str, Any]:
        wan_iface = state.get_wan_interface() or ""
        return {
            "bridge": state.bridge,
            "firewall": state.firewall,
            "interfaces": state.interfaces,
            "lan_ifaces": state.get_lan_interfaces(),
            "pppoe": state.pppoe,
            "router": state.router_info,
            "rules": state.firewall.rules,
            "vlans": state.vlans,
            "wan_iface": wan_iface,
        }

    def _version_folder(self, state: AppState) -> str:
        if state.router_info and state.router_info.major == 6:
            return "v6"
        return "v7"

    def _pppoe_commands(self, state: AppState) -> list[RouterCommand]:
        if not state.pppoe.enabled or not state.pppoe.wan_iface:
            return []

        return [
            RouterCommand(
                label="Create PPPoE client pppoe-out1",
                path="/interface/pppoe-client/add",
                check_path="/interface/pppoe-client/print",
                ensure_filters={"name": "pppoe-out1"},
                params={
                    "name": "pppoe-out1",
                    "interface": state.pppoe.wan_iface,
                    "user": state.pppoe.username,
                    "password": state.pppoe.password,
                    "service-name": state.pppoe.service_name,
                    "add-default-route": True,
                    "use-peer-dns": True,
                    "disabled": False,
                },
            )
        ]

    def _bridge_commands(self, state: AppState) -> list[RouterCommand]:
        lan_ifaces = state.get_lan_interfaces()
        if not lan_ifaces and not state.vlans:
            return []

        commands = [
            RouterCommand(
                label=f"Create bridge {state.bridge.name}",
                path="/interface/bridge/add",
                check_path="/interface/bridge/print",
                ensure_filters={"name": state.bridge.name},
                params={
                    "name": state.bridge.name,
                    "protocol-mode": state.bridge.protocol,
                    "vlan-filtering": state.bridge.vlan_filtering and self._version_folder(state) == "v7",
                },
            )
        ]

        for iface_name in lan_ifaces:
            commands.append(
                RouterCommand(
                    label=f"Add {iface_name} to {state.bridge.name}",
                    path="/interface/bridge/port/add",
                    check_path="/interface/bridge/port/print",
                    ensure_filters={"interface": iface_name, "bridge": state.bridge.name},
                    params={
                        "bridge": state.bridge.name,
                        "interface": iface_name,
                    },
                )
            )

        return commands

    def _firewall_commands(self, state: AppState) -> list[RouterCommand]:
        wan_iface = state.get_wan_interface()
        if not wan_iface:
            return []

        rules = state.firewall.rules
        commands: list[RouterCommand] = []

        if rules.accept_established:
            commands.append(
                self._firewall_filter(
                    "Accept established input",
                    chain="input",
                    comment="mtk-auto accept established input",
                    **{"connection-state": "established,related", "action": "accept"},
                )
            )
            commands.append(
                self._firewall_filter(
                    "Accept established forward",
                    chain="forward",
                    comment="mtk-auto accept established forward",
                    **{"connection-state": "established,related", "action": "accept"},
                )
            )

        if rules.drop_invalid:
            commands.append(
                self._firewall_filter(
                    "Drop invalid input",
                    chain="input",
                    comment="mtk-auto drop invalid",
                    **{"connection-state": "invalid", "action": "drop"},
                )
            )

        if rules.accept_icmp:
            commands.append(
                self._firewall_filter(
                    "Accept ICMP",
                    chain="input",
                    protocol="icmp",
                    action="accept",
                    comment="mtk-auto accept icmp",
                )
            )

        if rules.accept_lan_input and state.bridge.name:
            commands.append(
                self._firewall_filter(
                    "Accept LAN input",
                    chain="input",
                    **{
                        "in-interface": state.bridge.name,
                        "action": "accept",
                        "comment": "mtk-auto accept lan input",
                    },
                )
            )

        if rules.port_scan_detection:
            commands.append(
                self._firewall_filter(
                    "Drop port scans",
                    chain="input",
                    protocol="tcp",
                    **{
                        "psd": "21,3s,3,1",
                        "action": "drop",
                        "comment": "mtk-auto port scan",
                    },
                )
            )

        if rules.ssh_bruteforce:
            commands.append(
                self._firewall_filter(
                    "Protect SSH",
                    chain="input",
                    protocol="tcp",
                    **{
                        "dst-port": "22",
                        "connection-limit": "3,32",
                        "action": "drop",
                        "comment": "mtk-auto ssh bruteforce",
                    },
                )
            )

        if rules.bogon_drop:
            commands.append(
                self._firewall_filter(
                    "Drop bogons on WAN",
                    chain="input",
                    **{
                        "in-interface": wan_iface,
                        "src-address-list": "not_in_internet",
                        "action": "drop",
                        "comment": "mtk-auto bogon drop",
                    },
                )
            )

        if rules.rate_limit_new:
            commands.append(
                self._firewall_filter(
                    "Rate-limit new input",
                    chain="input",
                    **{
                        "connection-state": "new",
                        "limit": "50,5:packet",
                        "action": "accept",
                        "comment": "mtk-auto rate limit new",
                    },
                )
            )

        if rules.explicit_forward:
            commands.append(
                self._firewall_filter(
                    "Default forward drop",
                    chain="forward",
                    **{"action": "drop", "comment": "mtk-auto default forward drop"},
                )
            )

        if rules.log_drops:
            commands.append(
                self._firewall_filter(
                    "Log WAN drops",
                    chain="input",
                    **{
                        "in-interface": wan_iface,
                        "action": "log",
                        "log-prefix": "MTK-DROP ",
                        "comment": "mtk-auto log drops",
                    },
                )
            )

        if rules.masquerade:
            commands.append(
                RouterCommand(
                    label="Add NAT masquerade",
                    path="/ip/firewall/nat/add",
                    check_path="/ip/firewall/nat/print",
                    ensure_filters={"comment": "mtk-auto nat masquerade"},
                    params={
                        "chain": "srcnat",
                        "out-interface": wan_iface,
                        "action": "masquerade",
                        "comment": "mtk-auto nat masquerade",
                    },
                )
            )

        if rules.raw_table and self._version_folder(state) == "v7":
            commands.append(
                RouterCommand(
                    label="Add raw DNS amplification guard",
                    path="/ip/firewall/raw/add",
                    check_path="/ip/firewall/raw/print",
                    ensure_filters={"comment": "mtk-auto raw dns amp"},
                    params={
                        "chain": "prerouting",
                        "protocol": "udp",
                        "dst-port": "53",
                        "action": "drop",
                        "comment": "mtk-auto raw dns amp",
                    },
                )
            )

        return commands

    def _vlan_commands(self, state: AppState) -> list[RouterCommand]:
        if not state.vlans:
            return []

        commands: list[RouterCommand] = []
        for vlan in state.vlans:
            commands.append(
                RouterCommand(
                    label=f"Create VLAN interface {vlan.interface_name}",
                    path="/interface/vlan/add",
                    check_path="/interface/vlan/print",
                    ensure_filters={"name": vlan.interface_name},
                    params={
                        "name": vlan.interface_name,
                        "vlan-id": vlan.vlan_id,
                        "interface": state.bridge.name,
                    },
                )
            )

            if self._version_folder(state) == "v7":
                commands.append(
                    RouterCommand(
                        label=f"Add bridge VLAN {vlan.vlan_id}",
                        path="/interface/bridge/vlan/add",
                        check_path="/interface/bridge/vlan/print",
                        ensure_filters={"bridge": state.bridge.name, "vlan-ids": vlan.vlan_id},
                        params={
                            "bridge": state.bridge.name,
                            "vlan-ids": vlan.vlan_id,
                            "tagged": ",".join([state.bridge.name, *vlan.tagged_ports]),
                            "untagged": ",".join(vlan.untagged_ports),
                        },
                    )
                )

        return commands

    def _firewall_filter(self, label: str, **params: Any) -> RouterCommand:
        comment = str(params.get("comment", label))
        return RouterCommand(
            label=label,
            path="/ip/firewall/filter/add",
            check_path="/ip/firewall/filter/print",
            ensure_filters={"comment": comment},
            params=params,
        )

    def _exists(self, connection: Any, command: RouterCommand) -> bool:
        if not command.check_path or not command.ensure_filters:
            return False

        query = {
            f"?{key}": self._serialize_value(value)
            for key, value in command.ensure_filters.items()
            if value not in {"", None}
        }

        rows = connection.run_command(command.check_path, **query)
        return bool(rows)

    def _serialize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            key: self._serialize_value(value)
            for key, value in params.items()
            if value not in {None, ""}
        }

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, bool):
            return "yes" if value else "no"
        return value
