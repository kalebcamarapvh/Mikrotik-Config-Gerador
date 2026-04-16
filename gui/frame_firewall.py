from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from core.firewall import PRESET_DETAILS, RULE_METADATA, build_firewall_config, build_firewall_rules
from core.models import FirewallConfig, FirewallRules


class FirewallFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master)
        self.app = app
        self.rule_vars: dict[str, tk.BooleanVar] = {}
        self.preset_var = tk.StringVar(value="basic")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        header.grid_columnconfigure((0, 1, 2), weight=1)

        for column, preset in enumerate(["basic", "medium", "advanced"]):
            ctk.CTkRadioButton(
                header,
                text=preset.title(),
                value=preset,
                variable=self.preset_var,
                command=self.apply_preset,
            ).grid(row=0, column=column, sticky="w", padx=12, pady=12)

        ctk.CTkButton(header, text="What does this add?", command=self.show_preset_details).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            padx=12,
            pady=(0, 12),
        )

        self.rules_frame = ctk.CTkScrollableFrame(self)
        self.rules_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.rules_frame.grid_columnconfigure(0, weight=1)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        actions.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(actions, text="Back", command=lambda: self.app.show_step("interfaces")).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ctk.CTkButton(actions, text="Next", command=self.save_and_next).grid(
            row=0, column=1, sticky="ew", padx=4
        )

    def refresh_from_state(self) -> None:
        self.preset_var.set(self.app.state.firewall.preset)
        self._build_rule_checkboxes(self.app.state.firewall.rules)

    def apply_preset(self) -> None:
        self._build_rule_checkboxes(build_firewall_rules(self.preset_var.get()))

    def show_preset_details(self) -> None:
        preset = self.preset_var.get()
        details = PRESET_DETAILS[preset]
        messagebox.showinfo(preset.title(), "\n".join(f"- {item}" for item in details))

    def save_and_next(self) -> None:
        rules = FirewallRules(
            **{name: variable.get() for name, variable in self.rule_vars.items()}
        )
        self.app.state.firewall = FirewallConfig(preset=self.preset_var.get(), rules=rules)
        self.app.show_step("vlan")

    def _build_rule_checkboxes(self, rules: FirewallRules) -> None:
        for child in self.rules_frame.winfo_children():
            child.destroy()

        self.rule_vars.clear()
        for row, (name, label) in enumerate(RULE_METADATA.items()):
            variable = tk.BooleanVar(value=getattr(rules, name))
            self.rule_vars[name] = variable
            ctk.CTkCheckBox(self.rules_frame, text=label, variable=variable).grid(
                row=row,
                column=0,
                sticky="w",
                padx=12,
                pady=8,
            )
