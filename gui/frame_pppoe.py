from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from core.models import PPPoEConfig


class PPPoEFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master)
        self.app = app

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.wan_var = tk.StringVar(value="")
        self.user_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.service_var = tk.StringVar()

        form = ctk.CTkFrame(self)
        form.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=12, pady=12)
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="WAN Interface").grid(row=0, column=0, sticky="w", padx=16, pady=12)
        self.wan_menu = ctk.CTkOptionMenu(form, variable=self.wan_var, values=[""])
        self.wan_menu.grid(row=0, column=1, sticky="ew", padx=16, pady=12)

        ctk.CTkLabel(form, text="PPPoE Username").grid(row=1, column=0, sticky="w", padx=16, pady=12)
        ctk.CTkEntry(form, textvariable=self.user_var).grid(row=1, column=1, sticky="ew", padx=16, pady=12)

        ctk.CTkLabel(form, text="PPPoE Password").grid(row=2, column=0, sticky="w", padx=16, pady=12)
        ctk.CTkEntry(form, textvariable=self.password_var, show="*").grid(row=2, column=1, sticky="ew", padx=16, pady=12)

        ctk.CTkLabel(form, text="Service Name").grid(row=3, column=0, sticky="w", padx=16, pady=12)
        ctk.CTkEntry(form, textvariable=self.service_var).grid(row=3, column=1, sticky="ew", padx=16, pady=12)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        actions.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(actions, text="Back", command=lambda: self.app.show_step("connect")).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ctk.CTkButton(actions, text="Skip PPPoE", command=self.skip_pppoe).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ctk.CTkButton(actions, text="Next", command=self.save_and_next).grid(
            row=0, column=2, sticky="ew", padx=4
        )

    def refresh_from_state(self) -> None:
        values = [interface.name for interface in self.app.state.interfaces if interface.is_physical]
        if not values:
            values = [""]
        self.wan_menu.configure(values=values)

        current = self.app.state.pppoe.wan_iface or (values[0] if values else "")
        self.wan_var.set(current)
        self.user_var.set(self.app.state.pppoe.username)
        self.password_var.set(self.app.state.pppoe.password)
        self.service_var.set(self.app.state.pppoe.service_name)

    def skip_pppoe(self) -> None:
        self.app.state.pppoe = PPPoEConfig(enabled=False)
        self.app.state.ensure_pppoe_wan_lock()
        self.app.refresh_frames()
        self.app.show_step("interfaces")

    def save_and_next(self) -> None:
        wan_iface = self.wan_var.get().strip()
        if not wan_iface:
            messagebox.showerror("Missing WAN interface", "Select the interface that will carry PPPoE.")
            return

        self.app.state.pppoe = PPPoEConfig(
            enabled=True,
            wan_iface=wan_iface,
            username=self.user_var.get().strip(),
            password=self.password_var.get(),
            service_name=self.service_var.get().strip(),
        )
        self.app.state.ensure_pppoe_wan_lock()
        self.app.refresh_frames()
        self.app.show_step("interfaces")
