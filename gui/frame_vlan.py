from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from pydantic import ValidationError

from core.models import BridgeConfig, VLANConfig


class VLANFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master)
        self.app = app
        self.vlan_rows: list[dict[str, tk.StringVar]] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        top.grid_columnconfigure(1, weight=1)

        self.bridge_name_var = tk.StringVar(value=self.app.state.bridge.name)
        self.protocol_var = tk.StringVar(value=self.app.state.bridge.protocol.upper())
        self.vlan_filtering_var = tk.BooleanVar(value=self.app.state.bridge.vlan_filtering)

        ctk.CTkLabel(top, text="Bridge Name").grid(row=0, column=0, sticky="w", padx=12, pady=10)
        ctk.CTkEntry(top, textvariable=self.bridge_name_var).grid(row=0, column=1, sticky="ew", padx=12, pady=10)

        ctk.CTkLabel(top, text="Bridge Protocol").grid(row=1, column=0, sticky="w", padx=12, pady=10)
        ctk.CTkOptionMenu(top, variable=self.protocol_var, values=["RSTP", "STP", "NONE"]).grid(
            row=1, column=1, sticky="ew", padx=12, pady=10
        )

        ctk.CTkCheckBox(top, text="Enable VLAN filtering", variable=self.vlan_filtering_var).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=12, pady=10
        )

        self.table = ctk.CTkScrollableFrame(self)
        self.table.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.table.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkButton(self, text="+ Add VLAN", command=self.add_vlan_row).grid(
            row=2, column=0, sticky="w", padx=12, pady=(0, 8)
        )

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        actions.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(actions, text="Back", command=lambda: self.app.show_step("firewall")).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ctk.CTkButton(actions, text="Next", command=self.save_and_next).grid(
            row=0, column=1, sticky="ew", padx=4
        )

    def refresh_from_state(self) -> None:
        self.bridge_name_var.set(self.app.state.bridge.name)
        self.protocol_var.set(self.app.state.bridge.protocol.upper())
        self.vlan_filtering_var.set(self.app.state.bridge.vlan_filtering)

        for child in self.table.winfo_children():
            child.destroy()
        self.vlan_rows.clear()

        self._render_headers()
        if self.app.state.vlans:
            for vlan in self.app.state.vlans:
                self.add_vlan_row(vlan.vlan_id, vlan.name, vlan.tagged_ports, vlan.untagged_ports)

    def add_vlan_row(
        self,
        vlan_id: int | None = None,
        name: str = "",
        tagged_ports: list[str] | None = None,
        untagged_ports: list[str] | None = None,
    ) -> None:
        if not self.vlan_rows:
            self._render_headers()

        row_index = len(self.vlan_rows) + 1
        data = {
            "vlan_id": tk.StringVar(value="" if vlan_id is None else str(vlan_id)),
            "name": tk.StringVar(value=name),
            "tagged_ports": tk.StringVar(value=", ".join(tagged_ports or [])),
            "untagged_ports": tk.StringVar(value=", ".join(untagged_ports or [])),
        }
        self.vlan_rows.append(data)

        ctk.CTkEntry(self.table, textvariable=data["vlan_id"]).grid(
            row=row_index, column=0, sticky="ew", padx=8, pady=8
        )
        ctk.CTkEntry(self.table, textvariable=data["name"]).grid(
            row=row_index, column=1, sticky="ew", padx=8, pady=8
        )
        ctk.CTkEntry(self.table, textvariable=data["tagged_ports"]).grid(
            row=row_index, column=2, sticky="ew", padx=8, pady=8
        )
        ctk.CTkEntry(self.table, textvariable=data["untagged_ports"]).grid(
            row=row_index, column=3, sticky="ew", padx=8, pady=8
        )

    def save_and_next(self) -> None:
        try:
            bridge = BridgeConfig(
                name=self.bridge_name_var.get().strip() or "bridge-lan",
                protocol=self.protocol_var.get().lower(),
                vlan_filtering=self.vlan_filtering_var.get(),
            )
            vlans = self._collect_vlans()
        except (ValidationError, ValueError) as exc:
            messagebox.showerror("Invalid VLAN configuration", str(exc))
            return

        self.app.state.bridge = bridge
        self.app.state.vlans = vlans
        self.app.show_step("summary")

    def _collect_vlans(self) -> list[VLANConfig]:
        vlans: list[VLANConfig] = []
        for row in self.vlan_rows:
            vlan_id_text = row["vlan_id"].get().strip()
            name = row["name"].get().strip()
            tagged = _split_csv(row["tagged_ports"].get())
            untagged = _split_csv(row["untagged_ports"].get())

            if not vlan_id_text and not name and not tagged and not untagged:
                continue

            vlans.append(
                VLANConfig(
                    vlan_id=int(vlan_id_text),
                    name=name,
                    tagged_ports=tagged,
                    untagged_ports=untagged,
                )
            )
        return vlans

    def _render_headers(self) -> None:
        headers = ["VLAN ID", "Name", "Tagged Ports", "Untagged Ports"]
        for column, label in enumerate(headers):
            ctk.CTkLabel(self.table, text=label, anchor="w").grid(
                row=0,
                column=column,
                sticky="ew",
                padx=8,
                pady=(4, 8),
            )


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
