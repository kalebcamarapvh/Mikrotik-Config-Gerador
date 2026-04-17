from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from core.firewall import get_preset_title


class SummaryFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master)
        self.app = app

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.summary_box = ctk.CTkTextbox(self)
        self.summary_box.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 6))

        self.script_box = ctk.CTkTextbox(self)
        self.script_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(6, 12))
        actions.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(actions, text="Back", command=lambda: self.app.show_step("vlan")).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ctk.CTkButton(actions, text="Show Script", command=self.show_script).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ctk.CTkButton(actions, text="Apply to Router", command=self.apply_to_router).grid(
            row=0, column=2, sticky="ew", padx=4
        )

    def refresh_from_state(self) -> None:
        self._set_text(self.summary_box, self._build_summary())
        if self.app.state.generated_script:
            self._set_text(self.script_box, self.app.state.generated_script)

    def show_script(self) -> None:
        script = self.app.configurator.render_script(self.app.state)
        self._set_text(self.script_box, script or "# No script generated.")

    def apply_to_router(self) -> None:
        if not self.app.connection.is_connected():
            messagebox.showerror("Not connected", "Connect to a router before applying the configuration.")
            return

        script = self.app.configurator.render_script(self.app.state)
        self._set_text(self.script_box, script or "# No script generated.")
        self._set_text(self.summary_box, self._build_summary())

        progress_lines: list[str] = []

        def append(message: str) -> None:
            progress_lines.append(message)
            combined = self._build_summary() + "\n\nApply Log\n---------\n" + "\n".join(progress_lines)
            self._set_text(self.summary_box, combined)
            self.update_idletasks()

        self.app.configurator.apply(self.app.state, self.app.connection, progress=append)

    def _build_summary(self) -> str:
        router = self.app.state.router_info
        lines = ["Configuration Summary", "---------------------"]

        if router:
            lines.append(f"Board: {router.board or '-'}")
            lines.append(f"RouterOS: {router.full or '-'}")
            lines.append(f"Identity: {router.identity or '-'}")
        else:
            lines.append("Router: not connected")

        wan = self.app.state.get_wan_interface() or "-"
        lines.extend(
            [
                "",
                f"PPPoE: {'enabled' if self.app.state.pppoe.enabled else 'disabled'}",
                f"WAN interface: {wan}",
                "",
                "Interfaces:",
            ]
        )

        if not self.app.state.interface_assignments:
            lines.append("  - none detected")
        else:
            for assignment in self.app.state.interface_assignments.values():
                lines.append(f"  - {assignment.name}: {assignment.role.upper()}")

        lines.extend(
            [
                "",
                f"Firewall preset: {get_preset_title(self.app.state.firewall.preset)}",
                f"Bridge: {self.app.state.bridge.name} ({self.app.state.bridge.protocol.upper()})",
                f"VLAN filtering: {'on' if self.app.state.bridge.vlan_filtering else 'off'}",
                "",
                "VLANs:",
            ]
        )

        if not self.app.state.vlans:
            lines.append("  - none")
        else:
            for vlan in self.app.state.vlans:
                lines.append(f"  - VLAN {vlan.vlan_id}: {vlan.name}")

        return "\n".join(lines)

    @staticmethod
    def _set_text(widget: ctk.CTkTextbox, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
