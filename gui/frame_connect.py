from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from core.detector import discover_interfaces, summarize_ports


class ConnectFrame(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master)
        self.app = app

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.host_var = tk.StringVar(value=self.app.state.host)
        self.port_var = tk.StringVar(value=str(self.app.state.port))
        self.user_var = tk.StringVar(value=self.app.state.username)
        self.password_var = tk.StringVar(value=self.app.state.password)

        form = ctk.CTkFrame(self)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        form.grid_columnconfigure(1, weight=1)

        fields = [
            ("Router IP / Hostname", self.host_var, False),
            ("API Port", self.port_var, False),
            ("Username", self.user_var, False),
            ("Password", self.password_var, True),
        ]

        for row, (label_text, variable, is_password) in enumerate(fields):
            ctk.CTkLabel(form, text=label_text).grid(row=row, column=0, sticky="w", padx=16, pady=12)
            entry_kwargs = {"textvariable": variable}
            if is_password:
                entry_kwargs["show"] = "*"
            entry = ctk.CTkEntry(form, **entry_kwargs)
            entry.grid(row=row, column=1, sticky="ew", padx=16, pady=12)

        ctk.CTkButton(
            form,
            text="Connect and Detect",
            command=self.connect_and_detect,
        ).grid(row=len(fields), column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 16))

        info = ctk.CTkFrame(self)
        info.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        info.grid_columnconfigure(1, weight=1)

        self.info_vars = {
            "Board": tk.StringVar(value="-"),
            "Version": tk.StringVar(value="-"),
            "RAM": tk.StringVar(value="-"),
            "Ports": tk.StringVar(value="-"),
            "Identity": tk.StringVar(value="-"),
        }

        for row, (label_text, variable) in enumerate(self.info_vars.items()):
            ctk.CTkLabel(info, text=label_text, width=90).grid(row=row, column=0, sticky="w", padx=16, pady=10)
            ctk.CTkLabel(info, textvariable=variable, anchor="w").grid(
                row=row,
                column=1,
                sticky="ew",
                padx=16,
                pady=10,
            )

    def refresh_from_state(self) -> None:
        self.host_var.set(self.app.state.host)
        self.port_var.set(str(self.app.state.port))
        self.user_var.set(self.app.state.username)
        self.password_var.set(self.app.state.password)

        router = self.app.state.router_info
        if not router:
            return

        self.info_vars["Board"].set(router.board or "-")
        self.info_vars["Version"].set(f"RouterOS {router.full}" if router.full else "-")
        self.info_vars["RAM"].set(f"{router.ram_mb} MB" if router.ram_mb else "-")
        self.info_vars["Ports"].set(summarize_ports(self.app.state.interfaces))
        self.info_vars["Identity"].set(router.identity or "-")

    def connect_and_detect(self) -> None:
        self.app.state.host = self.host_var.get().strip()
        self.app.state.username = self.user_var.get().strip()
        self.app.state.password = self.password_var.get()

        try:
            self.app.state.port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid port", "API port must be a valid integer.")
            return

        self.app.set_status("Connecting to router...")
        connected = self.app.connection.connect(
            host=self.app.state.host,
            user=self.app.state.username,
            password=self.app.state.password,
            port=self.app.state.port,
        )
        if not connected:
            messagebox.showerror("Connection failed", self.app.connection.last_error or "Unknown connection error.")
            self.app.set_status("Connection failed.")
            return

        try:
            router = self.app.connection.detect_version()
            interfaces = discover_interfaces(self.app.connection)
        except Exception as exc:
            messagebox.showerror("Detection failed", str(exc))
            self.app.set_status("Connected, but detection failed.")
            return

        self.app.state.router_info = router
        self.app.state.interfaces = interfaces
        self.app.state.sync_interface_assignments()
        self.app.state.ensure_pppoe_wan_lock()
        self.refresh_from_state()
        self.app.refresh_frames()
        self.app.set_status(f"Connected to {router.identity or self.app.state.host}.")
        self.app.show_step("pppoe")
