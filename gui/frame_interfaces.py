from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from core.models import InterfaceAssignment


ROLE_OPTIONS = ["WAN", "LAN", "Unused", "Skip"]


class InterfacesFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master)
        self.app = app
        self.role_vars: dict[str, tk.StringVar] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.scroll.grid_columnconfigure(1, weight=1)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        actions.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(actions, text="Back", command=lambda: self.app.show_step("pppoe")).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ctk.CTkButton(actions, text="Next", command=self.save_and_next).grid(
            row=0, column=1, sticky="ew", padx=4
        )

    def refresh_from_state(self) -> None:
        self.app.state.sync_interface_assignments()
        self.app.state.ensure_pppoe_wan_lock()

        for child in self.scroll.winfo_children():
            child.destroy()
        self.role_vars.clear()

        for row, interface in enumerate(self.app.state.interfaces):
            assignment = self.app.state.interface_assignments.get(interface.name)
            display_role = (assignment.role if assignment else "skip").upper()
            variable = tk.StringVar(value=display_role)
            self.role_vars[interface.name] = variable

            ctk.CTkLabel(self.scroll, text=interface.name, anchor="w").grid(
                row=row,
                column=0,
                sticky="ew",
                padx=12,
                pady=10,
            )

            menu = ctk.CTkOptionMenu(self.scroll, values=ROLE_OPTIONS, variable=variable)
            menu.grid(row=row, column=1, sticky="ew", padx=12, pady=10)

            if assignment and assignment.locked:
                menu.configure(state="disabled")

    def save_and_next(self) -> None:
        assignments: dict[str, InterfaceAssignment] = {}
        wan_count = 0

        for name, variable in self.role_vars.items():
            role = variable.get().lower()
            if role == "wan":
                wan_count += 1

            existing = self.app.state.interface_assignments.get(name)
            assignments[name] = InterfaceAssignment(
                name=name,
                role=role,
                locked=bool(existing and existing.locked),
            )

        if wan_count > 1:
            messagebox.showerror("Invalid roles", "Only one interface can be WAN.")
            return

        self.app.state.interface_assignments = assignments
        self.app.show_step("firewall")
