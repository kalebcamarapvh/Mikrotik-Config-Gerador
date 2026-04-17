from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from core.firewall import (
    CHAIN_LABELS,
    CHAIN_ORDER,
    PRESET_DETAILS,
    PRESET_ORDER,
    RULE_METADATA,
    build_firewall_rules,
    get_preset_title,
    normalize_preset_name,
)
from core.models import FirewallConfig, FirewallRules


class FirewallFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master)
        self.app = app
        self.rule_vars: dict[str, tk.BooleanVar] = {}
        self.preset_var = tk.StringVar(value="recommended")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        header.grid_columnconfigure((0, 1, 2), weight=1)

        for column, preset in enumerate(PRESET_ORDER):
            ctk.CTkRadioButton(
                header,
                text=get_preset_title(preset),
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
        self.preset_var.set(normalize_preset_name(self.app.state.firewall.preset))
        self._build_rule_checkboxes(self.app.state.firewall.rules)

    def apply_preset(self) -> None:
        self._build_rule_checkboxes(build_firewall_rules(self.preset_var.get()))

    def show_preset_details(self) -> None:
        preset = self.preset_var.get()
        details = PRESET_DETAILS[preset]
        messagebox.showinfo(details["title"], "\n".join(f"- {item}" for item in details["includes"]))

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
        row = 0
        for chain in CHAIN_ORDER:
            ctk.CTkLabel(
                self.rules_frame,
                text=CHAIN_LABELS[chain],
                font=ctk.CTkFont(size=15, weight="bold"),
            ).grid(row=row, column=0, sticky="w", padx=12, pady=(12, 4))
            row += 1

            for name, data in RULE_METADATA.items():
                if data["chain"] != chain:
                    continue

                variable = tk.BooleanVar(value=getattr(rules, name))
                self.rule_vars[name] = variable

                line = ctk.CTkFrame(self.rules_frame, fg_color="transparent")
                line.grid(row=row, column=0, sticky="ew", padx=12, pady=4)
                line.grid_columnconfigure(1, weight=1)

                ctk.CTkCheckBox(line, text="", variable=variable).grid(
                    row=0,
                    column=0,
                    rowspan=2,
                    sticky="nw",
                    padx=(0, 8),
                    pady=4,
                )
                ctk.CTkLabel(
                    line,
                    text=data["title"],
                    font=ctk.CTkFont(weight="bold"),
                ).grid(row=0, column=1, sticky="w")
                ctk.CTkLabel(
                    line,
                    text=data["description"],
                    justify="left",
                    wraplength=640,
                ).grid(row=1, column=1, sticky="w", pady=(2, 0))
                row += 1
