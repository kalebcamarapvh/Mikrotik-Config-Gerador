from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from assistente_config_mikrotik import (
    DNS_PROFILE_ORDER,
    DNS_PROFILES,
    FIREWALL_CATEGORY_ORDER,
    FIREWALL_CATEGORY_TITLES,
    FIREWALL_OPTIONS,
    FIREWALL_PROFILE_ORDER,
    PERFIS_FIREWALL,
    SERVICOS_PADRAO,
    VLAN_PROFILE_ORDER,
    VLAN_PROFILE_PRESETS,
    criar_configuracao,
    gerar_script,
    normalizar_perfil_dns,
    normalizar_perfil_firewall,
    normalizar_interfaces_lan,
    obter_chaves_firewall_por_modo,
    obter_opcoes_firewall_padrao,
    obter_perfis_firewall_por_modo,
    obter_perfis_vlan_padrao,
    obter_servicos_padrao,
    parse_rede_lan,
)


COLORS = {
    "bg": "#F4F5F7",
    "card": "#FFFFFF",
    "border": "#D8DEE4",
    "primary": "#1F6F78",
    "primary_soft": "#DCEFF1",
    "accent": "#2E8B57",
    "accent_soft": "#DDF3E5",
    "warning": "#D98E04",
    "warning_soft": "#FFF1D6",
    "danger": "#B94A48",
    "danger_soft": "#F8E3E2",
    "muted": "#667085",
    "text": "#102A43",
}

MASK_OPTIONS = [
    "255.255.255.248 (/29)",
    "255.255.255.240 (/28)",
    "255.255.255.224 (/27)",
    "255.255.255.192 (/26)",
    "255.255.255.128 (/25)",
    "255.255.255.0 (/24)",
    "255.255.254.0 (/23)",
    "255.255.252.0 (/22)",
    "255.255.248.0 (/21)",
    "255.255.240.0 (/20)",
    "255.255.224.0 (/19)",
    "255.255.192.0 (/18)",
    "255.255.128.0 (/17)",
    "255.255.0.0 (/16)",
]

STEP_ORDER = ["versao", "internet", "rede_local", "seguranca", "resumo"]
INTERFACE_MODE_ORDER = ["basic", "advanced"]
INTERFACE_MODE_LABELS = {
    "basic": "Basico",
    "advanced": "Avancado",
}
DEFAULT_VLAN_KEYS = VLAN_PROFILE_ORDER[:2]
BANDWIDTH_PRESET_OPTIONS = [
    "Sem limite",
    "10M/10M",
    "20M/20M",
    "50M/50M",
    "100M/100M",
    "200M/200M",
    "Customizado",
]
STEP_TITLES = {
    "versao": "Versao",
    "internet": "Internet",
    "rede_local": "Rede Local",
    "seguranca": "Seguranca",
    "resumo": "Resumo",
}


class MikrotikGeneratorApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("MikroTik Config Generator")
        self.geometry("1200x820")
        self.minsize(1120, 760)
        self.configure(fg_color=COLORS["bg"])

        self.current_step = STEP_ORDER[0]
        self._content_row = 0
        self._pending_step_refresh = False
        self.status_var = tk.StringVar(value="Preencha os dados e gere o script.")
        self.inline_errors: dict[str, str] = {}
        self.script_preview = ""

        self.version_var = tk.IntVar(value=7)
        self.identity_var = tk.StringVar(value="MikroTik-v7")
        self.use_pppoe_var = tk.BooleanVar(value=True)
        self.pppoe_user_var = tk.StringVar()
        self.pppoe_password_var = tk.StringVar()
        self.pppoe_service_var = tk.StringVar()
        self.dns_profile_var = tk.StringVar(value="compatibility")
        self.dns_primary_var = tk.StringVar(value=str(DNS_PROFILES["compatibility"]["primario"]))
        self.dns_secondary_var = tk.StringVar(value=str(DNS_PROFILES["compatibility"]["secundario"]))
        self.wan_var = tk.StringVar(value="ether1")
        self.lan_var = tk.StringVar(value="ether2,ether3,ether4,ether5")
        self.network_var = tk.StringVar(value="192.168.10.0")
        self.mask_var = tk.StringVar(value=MASK_OPTIONS[0])
        self.dhcp_var = tk.BooleanVar(value=True)
        self.firewall_var = tk.StringVar(value="recommended")
        self.interface_mode_var = tk.StringVar(value="basic")
        self.password_visible = False
        self.custom_vlan_index = 0
        self.custom_vlan_keys: list[str] = []

        self.firewall_option_vars = {
            name: tk.BooleanVar(value=enabled)
            for name, enabled in obter_opcoes_firewall_padrao("recommended", self.version_var.get()).items()
        }
        self.vlan_profile_vars: dict[str, dict[str, tk.Variable]] = {}
        for item in obter_perfis_vlan_padrao():
            chave = str(item["chave"])
            vars_map = self._build_vlan_vars(item)
            self.vlan_profile_vars[chave] = vars_map
            self._register_vlan_vars(chave, vars_map)
        self.service_vars = {
            name: tk.BooleanVar(value=default)
            for name, default in obter_servicos_padrao().items()
        }

        self.step_labels: dict[str, tuple[ctk.CTkLabel, ctk.CTkLabel]] = {}
        self.step_items: dict[str, tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel]] = {}
        self.summary_value_labels: dict[str, ctk.CTkLabel] = {}
        self.summary_services_box: ctk.CTkTextbox | None = None
        self.content_title: ctk.CTkLabel | None = None
        self.content_subtitle: ctk.CTkLabel | None = None
        self.content_body: ctk.CTkFrame | None = None
        self.preview_box: ctk.CTkTextbox | None = None

        self._build_layout()
        self._render_interface_mode_controls()
        self._bind_live_updates()
        self._bind_navigation_shortcuts()
        self.show_step("versao")
        self.refresh_summary()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=20, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Gerador de Configuracao MikroTik",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Fluxo simples para gerar um .rsc pronto, com sugestoes em portugues.",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["muted"],
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.step_title_label = ctk.CTkLabel(
            header,
            text="Versao",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["primary"],
        )
        self.step_title_label.grid(row=0, column=1, sticky="e")

        self.interface_mode_frame = ctk.CTkFrame(header, fg_color="transparent")
        self.interface_mode_frame.grid(row=0, column=2, rowspan=2, sticky="e", padx=(16, 0))
        self.interface_mode_frame.grid_columnconfigure((0, 1), weight=0)
        ctk.CTkLabel(
            self.interface_mode_frame,
            text="Modo",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["muted"],
        ).grid(row=0, column=0, columnspan=2, sticky="e", pady=(0, 4))

        sidebar = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=22, border_width=1, border_color=COLORS["border"], width=190)
        sidebar.grid(row=1, column=0, sticky="ns", padx=(20, 12), pady=(0, 20))
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            sidebar,
            text="Passo a passo",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 6))
        ctk.CTkLabel(
            sidebar,
            text="Minha sugestao geral: RouterOS v7, firewall recomendado e so os servicos que voce realmente usa.",
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=150,
            text_color=COLORS["muted"],
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        for row, step in enumerate(STEP_ORDER, start=2):
            item = ctk.CTkFrame(sidebar, fg_color="transparent")
            item.grid(row=row, column=0, sticky="ew", padx=14, pady=4)
            item.grid_columnconfigure(1, weight=1)

            number = ctk.CTkLabel(
                item,
                text=str(row - 1),
                width=28,
                height=28,
                corner_radius=14,
                fg_color=COLORS["primary_soft"],
                text_color=COLORS["primary"],
                font=ctk.CTkFont(size=13, weight="bold"),
            )
            number.grid(row=0, column=0, padx=(4, 10), pady=6)

            label = ctk.CTkLabel(
                item,
                text=STEP_TITLES[step],
                anchor="w",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["text"],
            )
            label.grid(row=0, column=1, sticky="w")

            desc = ctk.CTkLabel(
                item,
                text=self._step_hint(step),
                anchor="w",
                justify="left",
                wraplength=120,
                font=ctk.CTkFont(size=11),
                text_color=COLORS["muted"],
            )
            desc.grid(row=1, column=1, sticky="w", pady=(0, 6))
            self.step_labels[step] = (label, number)
            self.step_items[step] = (item, label, desc)
            self._bind_step_navigation(item, step)
            self._bind_step_navigation(number, step)
            self._bind_step_navigation(label, step)
            self._bind_step_navigation(desc, step)

        content_shell = ctk.CTkFrame(
            self,
            fg_color=COLORS["card"],
            corner_radius=24,
            border_width=1,
            border_color=COLORS["border"],
        )
        content_shell.grid(row=1, column=1, sticky="nsew", padx=0, pady=(0, 20))
        content_shell.grid_rowconfigure(1, weight=1)
        content_shell.grid_columnconfigure(0, weight=1)

        header_card = ctk.CTkFrame(content_shell, fg_color="transparent")
        header_card.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 10))
        header_card.grid_columnconfigure(0, weight=1)

        self.content_title = ctk.CTkLabel(
            header_card,
            text="",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text"],
        )
        self.content_title.grid(row=0, column=0, sticky="w")
        self.content_subtitle = ctk.CTkLabel(
            header_card,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["muted"],
        )
        self.content_subtitle.grid(row=1, column=0, sticky="w", pady=(6, 0))

        self.content_body = ctk.CTkFrame(content_shell, fg_color="transparent")
        self.content_body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 18))
        self.content_body.grid_rowconfigure(0, weight=1)
        self.content_body.grid_columnconfigure(0, weight=1)

        summary = ctk.CTkFrame(
            self,
            fg_color=COLORS["card"],
            corner_radius=22,
            border_width=1,
            border_color=COLORS["border"],
            width=310,
        )
        summary.grid(row=1, column=2, sticky="ns", padx=(12, 20), pady=(0, 20))
        summary.grid_propagate(False)
        summary.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            summary,
            text="Resumo rapido",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))

        for row, title in enumerate(
            ["Versao", "PPPoE", "Rede LAN", "Firewall", "Servicos ligados"], start=1
        ):
            card = ctk.CTkFrame(summary, fg_color=COLORS["bg"], corner_radius=16)
            card.grid(row=row, column=0, sticky="ew", padx=16, pady=6)
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLORS["muted"],
            ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))

            if title == "Servicos ligados":
                self.summary_services_box = ctk.CTkTextbox(
                    card,
                    height=84,
                    border_width=0,
                    fg_color="transparent",
                    activate_scrollbars=False,
                    wrap="word",
                    font=ctk.CTkFont(size=12),
                    text_color=COLORS["text"],
                )
                self.summary_services_box.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
            else:
                value = ctk.CTkLabel(
                    card,
                    text="-",
                    justify="left",
                    anchor="w",
                    wraplength=240,
                    font=ctk.CTkFont(size=13),
                    text_color=COLORS["text"],
                )
                value.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))
                self.summary_value_labels[title] = value

        ctk.CTkLabel(
            summary,
            textvariable=self.status_var,
            justify="left",
            wraplength=250,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
        ).grid(row=10, column=0, sticky="sw", padx=18, pady=(12, 18))

    def _bind_live_updates(self) -> None:
        traced_vars: list[tk.Variable] = [
            self.identity_var,
            self.use_pppoe_var,
            self.pppoe_user_var,
            self.pppoe_password_var,
            self.pppoe_service_var,
            self.dns_profile_var,
            self.dns_primary_var,
            self.dns_secondary_var,
            self.wan_var,
            self.lan_var,
            self.network_var,
            self.mask_var,
            self.dhcp_var,
            self.firewall_var,
        ]
        traced_vars.extend(self.firewall_option_vars.values())
        traced_vars.extend(self.service_vars.values())

        for variable in traced_vars:
            self._bind_summary_var(variable)

        self.version_var.trace_add("write", lambda *_: self._handle_version_change())

    def _bind_navigation_shortcuts(self) -> None:
        self.bind("<Control-Right>", lambda _event: self.next_step())
        self.bind("<Control-Left>", lambda _event: self.previous_step())
        for index, step in enumerate(STEP_ORDER, start=1):
            self.bind(f"<Alt-Key-{index}>", lambda _event, target=step: self._go_to_step(target))
        self.bind("<Control-b>", lambda _event: self._set_interface_mode("basic"))
        self.bind("<Control-B>", lambda _event: self._set_interface_mode("basic"))
        self.bind("<Control-Shift-A>", lambda _event: self._set_interface_mode("advanced"))

    def _bind_step_navigation(self, widget: tk.Misc, step: str) -> None:
        widget.bind("<Button-1>", lambda _event, target=step: self._go_to_step(target))
        widget.configure(cursor="hand2")

    def _render_interface_mode_controls(self) -> None:
        for child in self.interface_mode_frame.winfo_children():
            if int(child.grid_info().get("row", 0)) > 0:
                child.destroy()

        for column, mode in enumerate(INTERFACE_MODE_ORDER):
            selected = self.interface_mode_var.get() == mode
            ctk.CTkButton(
                self.interface_mode_frame,
                text=INTERFACE_MODE_LABELS[mode],
                width=98,
                height=32,
                command=lambda value=mode: self._set_interface_mode(value),
                fg_color=COLORS["accent"] if selected else COLORS["primary_soft"],
                hover_color="#256D46" if selected else "#CAE6E8",
                text_color="#FFFFFF" if selected else COLORS["primary"],
            ).grid(row=1, column=column, padx=(0, 6) if column == 0 else (0, 0))

    def show_step(self, step: str) -> None:
        self.current_step = step
        self.step_title_label.configure(text=STEP_TITLES[step])
        self._update_step_rail()
        self._render_current_step()
        self.refresh_summary()

    def _go_to_step(self, step: str) -> None:
        if step == self.current_step:
            return

        current_index = STEP_ORDER.index(self.current_step)
        target_index = STEP_ORDER.index(step)
        if target_index <= current_index:
            self.show_step(step)
            return

        if self.validate_current_step():
            self.show_step(step)

    def next_step(self) -> None:
        if not self.validate_current_step():
            self._render_current_step()
            self.refresh_summary()
            return

        index = STEP_ORDER.index(self.current_step)
        if index < len(STEP_ORDER) - 1:
            self.show_step(STEP_ORDER[index + 1])

    def previous_step(self) -> None:
        index = STEP_ORDER.index(self.current_step)
        if index > 0:
            self.show_step(STEP_ORDER[index - 1])

    def validate_current_step(self) -> bool:
        self.inline_errors = {}

        if self.current_step == "internet":
            if not self.wan_var.get().strip():
                self.inline_errors["wan"] = "Informe a interface WAN."
            if self.use_pppoe_var.get():
                if not self.pppoe_user_var.get().strip():
                    self.inline_errors["pppoe_user"] = "Informe o usuario PPPoE."
                if not self.pppoe_password_var.get():
                    self.inline_errors["pppoe_password"] = "Informe a senha PPPoE."
            if self.dns_profile_var.get() == "custom":
                if not self.dns_primary_var.get().strip():
                    self.inline_errors["dns_primary"] = "Informe o DNS primario."
                try:
                    self._build_config()
                except ValueError as exc:
                    message = str(exc)
                    if "DNS primario" in message:
                        self.inline_errors["dns_primary"] = message
                    elif "DNS secundario" in message:
                        self.inline_errors["dns_secondary"] = message

        if self.current_step == "rede_local":
            try:
                parse_rede_lan(self.network_var.get(), self._selected_mask_value())
            except ValueError as exc:
                self.inline_errors["network"] = str(exc)

            try:
                normalizar_interfaces_lan(self.lan_var.get())
            except ValueError as exc:
                self.inline_errors["lan"] = str(exc)

            if self.wan_var.get().strip():
                try:
                    lan_ports = normalizar_interfaces_lan(self.lan_var.get())
                    if self.wan_var.get().strip() in lan_ports:
                        self.inline_errors["lan"] = "A WAN nao pode aparecer na lista de LAN."
                except ValueError:
                    pass

            if not self.inline_errors:
                try:
                    self._build_config()
                except ValueError as exc:
                    self.inline_errors["lan"] = str(exc)

        if self.current_step == "resumo":
            try:
                self.script_preview = gerar_script(self._build_config())
            except ValueError as exc:
                self.status_var.set(str(exc))
                previous = STEP_ORDER[STEP_ORDER.index("resumo") - 1]
                self.show_step(previous)
                return False

        if self.inline_errors:
            self.status_var.set("Corrija os campos destacados para continuar.")
            return False

        self.status_var.set("Tudo certo neste passo.")
        return True

    def _build_config(self):
        return criar_configuracao(
            versao_routeros=self.version_var.get(),
            identidade=self.identity_var.get(),
            usar_pppoe=self.use_pppoe_var.get(),
            pppoe_usuario=self.pppoe_user_var.get(),
            pppoe_senha=self.pppoe_password_var.get(),
            dns_profile=self.dns_profile_var.get(),
            dns_primario=self.dns_primary_var.get(),
            dns_secundario=self.dns_secondary_var.get(),
            rede=self.network_var.get(),
            mascara=self._selected_mask_value(),
            criar_dhcp=self.dhcp_var.get(),
            perfil_firewall=self.firewall_var.get(),
            servicos={name: variable.get() for name, variable in self.service_vars.items()},
            interface_wan=self.wan_var.get(),
            interfaces_lan=self.lan_var.get(),
            firewall_opcoes={name: variable.get() for name, variable in self.firewall_option_vars.items()},
            vlan_perfis=self._collect_vlan_profiles(),
        )

    def refresh_summary(self) -> None:
        self.summary_value_labels["Versao"].configure(
            text=f"RouterOS v{self.version_var.get()}"
        )

        pppoe_text = "Ativado" if self.use_pppoe_var.get() else "Desativado"
        if self.use_pppoe_var.get() and self.pppoe_user_var.get().strip():
            pppoe_text += f"\nUsuario: {self.pppoe_user_var.get().strip()}"
        pppoe_text += f"\nDNS: {DNS_PROFILES[normalizar_perfil_dns(self.dns_profile_var.get())]['titulo']}"
        self.summary_value_labels["PPPoE"].configure(text=pppoe_text)

        try:
            rede = parse_rede_lan(self.network_var.get(), self._selected_mask_value())
            vlan_names = self._enabled_vlan_profile_titles()
            vlan_text = f"\nVLANs: {', '.join(vlan_names)}" if vlan_names else "\nVLANs: nenhuma"
            lan_text = f"{rede.network_address}/{rede.prefixlen}\nGateway sugerido: {rede.network_address + 1}{vlan_text}"
        except ValueError:
            lan_text = "Preencha a rede para ver o resumo."
        self.summary_value_labels["Rede LAN"].configure(text=lan_text)

        self.summary_value_labels["Firewall"].configure(
            text=self._firewall_summary_text()
        )

        ativos = [label for name, label, _, _ in SERVICOS_PADRAO if self.service_vars[name].get()]
        services_text = ", ".join(ativos) if ativos else "Nenhum servico ligado."
        if self.summary_services_box is not None:
            self.summary_services_box.delete("1.0", "end")
            self.summary_services_box.insert("1.0", services_text)

        if self.current_step == "resumo" and self.preview_box is not None:
            self.refresh_preview()

    def refresh_preview(self) -> None:
        if self.preview_box is None:
            return

        try:
            self.script_preview = gerar_script(self._build_config())
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", self.script_preview)
            self.status_var.set("Script atualizado e pronto para salvar.")
        except ValueError as exc:
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", f"# Preencha os campos obrigatorios\n# {exc}\n")
            self.status_var.set(str(exc))

    def copy_script(self) -> None:
        self.refresh_preview()
        if not self.script_preview:
            return
        self.clipboard_clear()
        self.clipboard_append(self.script_preview)
        messagebox.showinfo("Script copiado", "O script foi copiado para a area de transferencia.")

    def save_script(self) -> None:
        self.refresh_preview()
        if not self.script_preview:
            return

        default_name = f"config_mikrotik_v{self.version_var.get()}.rsc"
        path = filedialog.asksaveasfilename(
            title="Salvar arquivo .rsc",
            defaultextension=".rsc",
            initialfile=default_name,
            filetypes=[("RouterOS Script", "*.rsc"), ("Todos os arquivos", "*.*")],
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.script_preview)
        messagebox.showinfo("Arquivo salvo", f"Script salvo em:\n{path}")

    def apply_service_suggestion(self) -> None:
        for name, default in obter_servicos_padrao().items():
            self.service_vars[name].set(default)
        self._refresh_security_step_if_visible()

    def enable_all_services(self) -> None:
        for variable in self.service_vars.values():
            variable.set(True)
        self._refresh_security_step_if_visible()

    def disable_insecure_services(self) -> None:
        seguros = {"winbox", "ssh"}
        for name, variable in self.service_vars.items():
            variable.set(name in seguros)
        self._refresh_security_step_if_visible()

    def _set_version(self, version: int) -> None:
        if self.version_var.get() != version:
            self.version_var.set(version)
        else:
            self._refresh_current_step_if_needed({"versao", "seguranca"})

    def _set_dns_profile(self, profile: str) -> None:
        profile = normalizar_perfil_dns(profile)
        self.dns_profile_var.set(profile)
        if profile != "custom":
            self.dns_primary_var.set(str(DNS_PROFILES[profile]["primario"]))
            self.dns_secondary_var.set(str(DNS_PROFILES[profile]["secundario"]))
        self._refresh_current_step_if_needed({"internet"})
        self.refresh_summary()

    def _set_interface_mode(self, mode: str) -> None:
        if mode not in INTERFACE_MODE_ORDER:
            return
        if self.interface_mode_var.get() == mode:
            return

        self.interface_mode_var.set(mode)
        if mode == "basic":
            visible_profiles = set(obter_perfis_firewall_por_modo("basic"))
            if self.firewall_var.get() not in visible_profiles:
                self.firewall_var.set("recommended")
            visible_keys = set(obter_chaves_firewall_por_modo("basic"))
            if self.firewall_var.get() == "custom":
                for name, variable in self.firewall_option_vars.items():
                    if name not in visible_keys:
                        variable.set(False)

        self._render_interface_mode_controls()
        self._refresh_current_step_if_needed({"internet", "rede_local", "seguranca"})

    def _handle_version_change(self) -> None:
        if self.identity_var.get().strip() in {"MikroTik-v6", "MikroTik-v7", ""}:
            self.identity_var.set(f"MikroTik-v{self.version_var.get()}")

        if self.firewall_var.get() != "custom":
            defaults = obter_opcoes_firewall_padrao(normalizar_perfil_firewall(self.firewall_var.get()), self.version_var.get())
            for name, value in defaults.items():
                self.firewall_option_vars[name].set(value)
        elif self.version_var.get() != 7:
            self.firewall_option_vars["raw_dns_v7"].set(False)

        self._refresh_current_step_if_needed({"versao", "seguranca"})

    def _set_firewall_profile(self, profile: str) -> None:
        profile = normalizar_perfil_firewall(profile)
        current = self.firewall_var.get()
        if current != profile:
            self.firewall_var.set(profile)

        if profile == "custom":
            # Custom: start from recommended defaults so user has a meaningful baseline to edit
            if current != "custom":
                defaults = obter_opcoes_firewall_padrao("recommended", self.version_var.get())
                for name, value in defaults.items():
                    self.firewall_option_vars[name].set(value)
            if self.version_var.get() != 7:
                self.firewall_option_vars["raw_dns_v7"].set(False)
        else:
            defaults = obter_opcoes_firewall_padrao(profile, self.version_var.get())
            for name, value in defaults.items():
                self.firewall_option_vars[name].set(value)

        self._refresh_security_step_if_visible()

    def _refresh_security_step_if_visible(self) -> None:
        self._refresh_current_step_if_needed({"seguranca"})

    def _refresh_current_step_and_summary(self) -> None:
        self._refresh_current_step_if_needed({"rede_local"})
        self.refresh_summary()

    def _refresh_current_step_if_needed(self, steps: set[str]) -> None:
        if self.current_step in steps:
            if not self._pending_step_refresh:
                self._pending_step_refresh = True
                self.after_idle(lambda: self._run_pending_step_refresh(steps))
            return
        self.refresh_summary()

    def _run_pending_step_refresh(self, steps: set[str]) -> None:
        self._pending_step_refresh = False
        if self.current_step in steps:
            self._render_current_step()
        self.refresh_summary()

    def toggle_password_visibility(self) -> None:
        self.password_visible = not self.password_visible
        self._render_current_step()

    def _render_current_step(self) -> None:
        assert self.content_body is not None
        for child in self.content_body.winfo_children():
            child.destroy()
        self._content_row = 0

        renderers = {
            "versao": self._render_version_step,
            "internet": self._render_internet_step,
            "rede_local": self._render_lan_step,
            "seguranca": self._render_security_step,
            "resumo": self._render_summary_step,
        }
        renderers[self.current_step]()

    def _render_version_step(self) -> None:
        self._set_content_header(
            "Qual versao do RouterOS voce vai configurar?",
            "Se voce nao tiver certeza, use v7.",
        )
        card = self._section_card(self.content_body)
        card.grid_columnconfigure((0, 1), weight=1)

        self._choice_card(
            card,
            row=0,
            column=0,
            title="RouterOS v7",
            description="Melhor suporte no gerador e regras avancadas.",
            selected=self.version_var.get() == 7,
            badge="Recomendado",
            badge_color=COLORS["accent_soft"],
            badge_text_color=COLORS["accent"],
            command=lambda: self._set_version(7),
        )
        self._choice_card(
            card,
            row=0,
            column=1,
            title="RouterOS v6",
            description="Compatibilidade legada para cenarios antigos.",
            selected=self.version_var.get() == 6,
            badge="Legado",
            badge_color=COLORS["warning_soft"],
            badge_text_color=COLORS["warning"],
            command=lambda: self._set_version(6),
        )

        form = self._section_card(self.content_body, pady=(18, 0))
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            form,
            text="Nome do roteador",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))
        ctk.CTkEntry(
            form,
            textvariable=self.identity_var,
            height=42,
            border_color=COLORS["border"],
            fg_color=COLORS["bg"],
        ).grid(row=0, column=1, sticky="ew", padx=18, pady=(18, 8))
        ctk.CTkLabel(
            form,
            text="Sugestao: use um nome simples para identificar esse cliente ou local.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 18))

        self._render_nav()

    def _render_internet_step(self) -> None:
        self._set_content_header(
            "Conexao com a internet",
            "Preencha apenas se sua operadora usar autenticacao PPPoE.",
        )
        scroll = ctk.CTkScrollableFrame(self.content_body, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        self._content_row = 0

        card = self._section_card(scroll)
        card.grid_columnconfigure(1, weight=1)
        card.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            card,
            text="Interface WAN",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))
        ctk.CTkEntry(
            card,
            textvariable=self.wan_var,
            height=42,
            border_color=COLORS["border"],
            fg_color=COLORS["bg"],
        ).grid(row=0, column=1, sticky="ew", padx=(0, 18), pady=(18, 8))

        ctk.CTkSwitch(
            card,
            text="Usar PPPoE",
            variable=self.use_pppoe_var,
            command=self._render_current_step,
            progress_color=COLORS["primary"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary"],
        ).grid(row=0, column=2, columnspan=2, sticky="w", padx=18, pady=(18, 8))

        self._error_label(card, "wan", row=1, column=0, columnspan=2)

        state = "normal" if self.use_pppoe_var.get() else "disabled"
        row_offset = 2
        for label, variable, key in [
            ("Usuario PPPoE", self.pppoe_user_var, "pppoe_user"),
            ("Senha PPPoE", self.pppoe_password_var, "pppoe_password"),
            ("Nome do servico PPPoE (opcional)", self.pppoe_service_var, ""),
        ]:
            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["text"],
            ).grid(row=row_offset, column=0, sticky="w", padx=18, pady=(10, 6))

            if key == "pppoe_password":
                field = ctk.CTkFrame(card, fg_color="transparent")
                field.grid(row=row_offset, column=1, columnspan=3, sticky="ew", padx=18, pady=(10, 6))
                field.grid_columnconfigure(0, weight=1)
                ctk.CTkEntry(
                    field,
                    textvariable=variable,
                    show="" if self.password_visible else "*",
                    state=state,
                    height=42,
                    border_color=COLORS["border"],
                    fg_color=COLORS["bg"],
                ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
                ctk.CTkButton(
                    field,
                    text="Ocultar" if self.password_visible else "Mostrar",
                    width=96,
                    command=self.toggle_password_visibility,
                    fg_color=COLORS["primary_soft"],
                    hover_color="#CAE6E8",
                    text_color=COLORS["primary"],
                ).grid(row=0, column=1)
            else:
                ctk.CTkEntry(
                    card,
                    textvariable=variable,
                    state=state,
                    height=42,
                    border_color=COLORS["border"],
                    fg_color=COLORS["bg"],
                ).grid(row=row_offset, column=1, columnspan=3, sticky="ew", padx=18, pady=(10, 6))

            if key:
                self._error_label(card, key, row=row_offset + 1, column=0, columnspan=4)
                row_offset += 2
            else:
                row_offset += 1

        ctk.CTkLabel(
            card,
            text="Se sua internet pega IP automaticamente e nao usa PPPoE, desligue a opcao acima.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
            wraplength=640,
            justify="left",
        ).grid(row=row_offset, column=0, columnspan=4, sticky="w", padx=18, pady=(8, 18))

        dns_card = self._section_card(scroll, pady=(16, 0))
        dns_card.grid_columnconfigure(0, weight=1)
        dns_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            dns_card,
            text="Perfis de DNS",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            dns_card,
            text="Escolha um conjunto pronto de resolvedores ou use Customizado para informar IPs manualmente.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 14))

        for idx, profile in enumerate(DNS_PROFILE_ORDER):
            data = DNS_PROFILES[profile]
            selected = self.dns_profile_var.get() == profile
            self._choice_card(
                dns_card,
                row=2 + idx // 2,
                column=idx % 2,
                title=data["titulo"],
                description=f"{data['descricao']}\nPrimario: {data['primario'] or '-'} | Secundario: {data['secundario'] or '-'}",
                selected=selected,
                badge="DNS",
                badge_color=COLORS["primary_soft"],
                badge_text_color=COLORS["primary"],
                command=lambda value=profile: self._set_dns_profile(value),
            )

        custom_state = "normal" if self.dns_profile_var.get() == "custom" else "disabled"
        ctk.CTkLabel(
            dns_card,
            text="DNS primario",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=4, column=0, sticky="w", padx=18, pady=(0, 6))
        ctk.CTkEntry(
            dns_card,
            textvariable=self.dns_primary_var,
            state=custom_state,
            height=42,
            border_color=COLORS["border"],
            fg_color=COLORS["bg"],
        ).grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 6))
        self._error_label(dns_card, "dns_primary", row=6, column=0)

        ctk.CTkLabel(
            dns_card,
            text="DNS secundario",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=4, column=1, sticky="w", padx=18, pady=(0, 6))
        ctk.CTkEntry(
            dns_card,
            textvariable=self.dns_secondary_var,
            state=custom_state,
            height=42,
            border_color=COLORS["border"],
            fg_color=COLORS["bg"],
        ).grid(row=5, column=1, sticky="ew", padx=18, pady=(0, 6))
        self._error_label(dns_card, "dns_secondary", row=6, column=1)

        self._render_nav(parent=scroll)

    def _render_lan_step(self) -> None:
        self._set_content_header(
            "Configuracao da rede local",
            "Defina a LAN principal e, se quiser, habilite perfis prontos de VLAN para expandir depois.",
        )
        scroll = ctk.CTkScrollableFrame(self.content_body, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        self._content_row = 0

        card = self._section_card(scroll)
        card.grid_columnconfigure(1, weight=1)
        card.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(card, text="Endereco da rede", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 8)
        )
        ctk.CTkEntry(
            card,
            textvariable=self.network_var,
            placeholder_text="192.168.10.0",
            height=42,
            border_color=COLORS["border"],
            fg_color=COLORS["bg"],
        ).grid(row=0, column=1, sticky="ew", padx=(0, 18), pady=(18, 8))

        ctk.CTkLabel(card, text="Mascara de sub-rede", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=2, sticky="w", padx=18, pady=(18, 8)
        )
        ctk.CTkOptionMenu(
            card,
            variable=self.mask_var,
            values=MASK_OPTIONS,
            height=42,
            fg_color=COLORS["primary"],
            button_color=COLORS["primary"],
            button_hover_color="#16555D",
        ).grid(row=0, column=3, sticky="ew", padx=(0, 18), pady=(18, 8))
        self._error_label(card, "network", row=1, column=0, columnspan=4)

        ctk.CTkLabel(card, text="Portas LAN na bridge", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=18, pady=(10, 8)
        )
        ctk.CTkEntry(
            card,
            textvariable=self.lan_var,
            height=42,
            border_color=COLORS["border"],
            fg_color=COLORS["bg"],
        ).grid(row=2, column=1, columnspan=3, sticky="ew", padx=18, pady=(10, 8))
        self._error_label(card, "lan", row=3, column=0, columnspan=4)

        ctk.CTkSwitch(
            card,
            text="Gerar DHCP automaticamente para a LAN",
            variable=self.dhcp_var,
            progress_color=COLORS["primary"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary"],
        ).grid(row=4, column=0, columnspan=4, sticky="w", padx=18, pady=(14, 10))

        details = self._derived_network_text()
        ctk.CTkLabel(
            card,
            text=details,
            justify="left",
            wraplength=640,
            font=ctk.CTkFont(size=13),
            text_color=COLORS["primary"],
        ).grid(row=5, column=0, columnspan=4, sticky="w", padx=18, pady=(0, 18))

        vlan_card = self._section_card(scroll, pady=(16, 0))
        vlan_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            vlan_card,
            text="Perfis de VLAN",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            vlan_card,
            text="Comece com Rede principal e Visitantes. Se precisar separar outro ambiente, clique em Adicionar VLAN para criar uma nova.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        ctk.CTkButton(
            vlan_card,
            text="Adicionar VLAN",
            command=self._add_custom_vlan,
            fg_color=COLORS["primary_soft"],
            hover_color="#CAE6E8",
            text_color=COLORS["primary"],
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 14))

        vlan_table = ctk.CTkFrame(vlan_card, fg_color=COLORS["bg"], corner_radius=16)
        vlan_table.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))
        vlan_table.grid_columnconfigure(0, weight=1)

        visible_vlan_keys = list(DEFAULT_VLAN_KEYS) + list(self.custom_vlan_keys)

        row = 0
        for chave in visible_vlan_keys:
            vars_map = self.vlan_profile_vars[chave]
            is_custom = chave.startswith("custom_")
            enabled = vars_map["enabled"].get()
            access_values = self._available_vlan_access_labels(chave)
            if vars_map["access_vlan"].get() not in access_values:
                vars_map["access_vlan"].set("Nenhuma")

            frame = ctk.CTkFrame(vlan_table, fg_color=COLORS["card"], corner_radius=16)
            frame.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
            frame.grid_columnconfigure(1, weight=1)
            frame.grid_columnconfigure(3, weight=1)

            ctk.CTkSwitch(
                frame,
                text=self._vlan_title_for_key(chave),
                variable=vars_map["enabled"],
                command=self._refresh_current_step_and_summary,
                progress_color=COLORS["primary"],
                button_color=COLORS["primary"],
                button_hover_color=COLORS["primary"],
            ).grid(row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(14, 4))
            if is_custom:
                ctk.CTkButton(
                    frame,
                    text="Remover",
                    width=90,
                    command=lambda target=chave: self._remove_custom_vlan(target),
                    fg_color=COLORS["danger_soft"],
                    hover_color="#F0CDCB",
                    text_color=COLORS["danger"],
                ).grid(row=0, column=3, sticky="e", padx=14, pady=(14, 4))
            ctk.CTkLabel(
                frame,
                text=self._vlan_description_for_key(chave),
                font=ctk.CTkFont(size=12),
                text_color=COLORS["muted"],
                wraplength=720,
                justify="left",
            ).grid(row=1, column=0, columnspan=4, sticky="w", padx=14, pady=(0, 12))

            state = "normal" if enabled else "disabled"

            info_row = 2
            if is_custom:
                ctk.CTkLabel(frame, text="Nome da VLAN", font=ctk.CTkFont(size=12, weight="bold")).grid(
                    row=2, column=0, sticky="w", padx=14, pady=(0, 6)
                )
                ctk.CTkEntry(
                    frame,
                    textvariable=vars_map["title"],
                    state=state,
                    height=38,
                    border_color=COLORS["border"],
                    fg_color=COLORS["bg"],
                    placeholder_text="Ex.: IoT, Cameras, ERP",
                ).grid(row=2, column=1, columnspan=3, sticky="ew", padx=(0, 14), pady=(0, 6))
                info_row = 3

            ctk.CTkLabel(frame, text="VLAN ID", font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=info_row, column=0, sticky="w", padx=14, pady=(0, 6)
            )
            ctk.CTkEntry(
                frame,
                textvariable=vars_map["vlan_id"],
                state=state,
                height=38,
                border_color=COLORS["border"],
                fg_color=COLORS["bg"],
            ).grid(row=info_row, column=1, sticky="ew", padx=(0, 14), pady=(0, 6))

            ctk.CTkLabel(frame, text="Rede", font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=info_row, column=2, sticky="w", padx=14, pady=(0, 6)
            )
            ctk.CTkEntry(
                frame,
                textvariable=vars_map["network"],
                state=state,
                height=38,
                border_color=COLORS["border"],
                fg_color=COLORS["bg"],
            ).grid(row=info_row, column=3, sticky="ew", padx=(0, 14), pady=(0, 6))

            flags = ctk.CTkFrame(frame, fg_color="transparent")
            flags.grid(row=info_row + 1, column=0, columnspan=4, sticky="ew", padx=14, pady=(6, 6))
            for column in range(3):
                flags.grid_columnconfigure(column, weight=1)

            for column, (text, var_key) in enumerate(
                [
                    ("Isolada das demais", "isolated"),
                    ("Acesso a internet", "internet_only"),
                    ("DHCP proprio", "dhcp"),
                ]
            ):
                ctk.CTkCheckBox(
                    flags,
                    text=text,
                    variable=vars_map[var_key],
                    state=state,
                    command=self.refresh_summary,
                ).grid(row=0, column=column, sticky="w", padx=(0, 12), pady=4)

            for column, (text, var_key) in enumerate(
                [
                    ("DNS proprio", "dns"),
                ]
            ):
                ctk.CTkCheckBox(
                    flags,
                    text=text,
                    variable=vars_map[var_key],
                    state=state,
                    command=self.refresh_summary,
                ).grid(row=1, column=column, sticky="w", padx=(0, 12), pady=4)

            ctk.CTkLabel(frame, text="Acesso a VLAN especifica", font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=info_row + 2, column=0, sticky="w", padx=14, pady=(8, 6)
            )
            ctk.CTkOptionMenu(
                frame,
                variable=vars_map["access_vlan"],
                values=access_values,
                state=state,
                height=38,
                fg_color=COLORS["primary"],
                button_color=COLORS["primary"],
                button_hover_color="#16555D",
                command=lambda _value: self.refresh_summary(),
            ).grid(row=info_row + 2, column=1, sticky="ew", padx=(0, 14), pady=(8, 6))

            ctk.CTkLabel(frame, text="Limite de banda", font=ctk.CTkFont(size=12, weight="bold")).grid(
                row=info_row + 2, column=2, sticky="w", padx=14, pady=(8, 6)
            )
            ctk.CTkOptionMenu(
                frame,
                variable=vars_map["bandwidth_preset"],
                values=BANDWIDTH_PRESET_OPTIONS,
                state=state,
                height=38,
                fg_color=COLORS["primary"],
                button_color=COLORS["primary"],
                button_hover_color="#16555D",
                command=lambda value, target=chave: self._set_vlan_bandwidth_preset(target, value),
            ).grid(row=info_row + 2, column=3, sticky="ew", padx=(0, 14), pady=(8, 6))

            ctk.CTkLabel(
                frame,
                text="Escolha um preset e, se quiser, apague e digite a banda que preferir.",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["muted"],
                justify="left",
                wraplength=720,
            ).grid(row=info_row + 3, column=0, columnspan=4, sticky="w", padx=14, pady=(0, 6))
            ctk.CTkEntry(
                frame,
                textvariable=vars_map["bandwidth"],
                state=state,
                height=38,
                border_color=COLORS["border"],
                fg_color=COLORS["bg"],
                placeholder_text="ex.: 20M/20M",
            ).grid(row=info_row + 4, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 14))

            row += 1

        self._render_nav()

    def _render_security_step(self) -> None:
        mode_label = INTERFACE_MODE_LABELS[self.interface_mode_var.get()].lower()
        basic_mode = self.interface_mode_var.get() == "basic"
        self._set_content_header(
            "Seguranca e Firewall",
            f"Escolha um perfil de firewall e ajuste os servicos de gerenciamento. O modo {mode_label} simplifica o que aparece aqui.",
        )

        # Single outer scrollable frame — avoid nesting CTkScrollableFrame inside another
        scroll = ctk.CTkScrollableFrame(self.content_body, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        self._content_row = 0

        # ── Firewall Profiles Card ──────────────────────────────────────────────
        firewall_card = self._section_card(scroll)
        firewall_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            firewall_card,
            text="Perfis de firewall",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            firewall_card,
            text="Escolha um perfil pronto ou use Customizado para marcar as opcoes de seguranca manualmente.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
            wraplength=800,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        mode_hint = ctk.CTkFrame(firewall_card, fg_color=COLORS["primary_soft"], corner_radius=14)
        mode_hint.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        mode_hint.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            mode_hint,
            text=(
                "Modo basico: mostra so os controles essenciais."
                if self.interface_mode_var.get() == "basic"
                else "Modo avancado: mostra todos os controles e opcoes disponiveis."
            ),
            font=ctk.CTkFont(size=12),
            text_color=COLORS["primary"],
            wraplength=780,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=10)

        profile_table = ctk.CTkFrame(firewall_card, fg_color=COLORS["bg"], corner_radius=16)
        profile_table.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))
        profile_table.grid_columnconfigure(0, weight=0, minsize=110)
        profile_table.grid_columnconfigure(1, weight=2)
        profile_table.grid_columnconfigure(2, weight=2)
        profile_table.grid_columnconfigure(3, weight=0, minsize=130)

        headers = ["Perfil", "Descricao", "Quando usar", "Acao"]
        for column, header in enumerate(headers):
            ctk.CTkLabel(
                profile_table,
                text=header,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["muted"],
            ).grid(row=0, column=column, sticky="w", padx=14, pady=(12, 8))

        visible_profiles = obter_perfis_firewall_por_modo(self.interface_mode_var.get())
        for row, profile in enumerate(visible_profiles, start=1):
            data = PERFIS_FIREWALL[profile]
            selected = self.firewall_var.get() == profile
            bg = COLORS["primary_soft"] if selected else COLORS["card"]
            border = COLORS["primary"] if selected else COLORS["border"]

            row_frame = ctk.CTkFrame(
                profile_table,
                fg_color=bg,
                border_width=1,
                border_color=border,
                corner_radius=14,
            )
            row_frame.grid(row=row, column=0, columnspan=4, sticky="ew", padx=8, pady=4)
            row_frame.grid_columnconfigure(0, weight=0, minsize=110)
            row_frame.grid_columnconfigure(1, weight=2)
            row_frame.grid_columnconfigure(2, weight=2)
            row_frame.grid_columnconfigure(3, weight=0, minsize=130)

            ctk.CTkLabel(
                row_frame,
                text=data["titulo"],
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["text"],
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=14, pady=14)
            ctk.CTkLabel(
                row_frame,
                text=data["descricao"],
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text"],
                wraplength=280,
                justify="left",
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=14, pady=14)
            ctk.CTkLabel(
                row_frame,
                text=data["quando_usar"],
                font=ctk.CTkFont(size=12),
                text_color=COLORS["muted"],
                wraplength=280,
                justify="left",
                anchor="w",
            ).grid(row=0, column=2, sticky="w", padx=14, pady=14)
            ctk.CTkButton(
                row_frame,
                text="Selecionado" if selected else "Usar",
                command=lambda value=profile: self._set_firewall_profile(value),
                width=120,
                fg_color=COLORS["accent"] if selected else COLORS["primary"],
                hover_color="#256D46" if selected else "#16555D",
            ).grid(row=0, column=3, padx=14, pady=14)

        custom_mode = self.firewall_var.get() == "custom"

        if basic_mode:
            simple_card = ctk.CTkFrame(firewall_card, fg_color=COLORS["bg"], corner_radius=16)
            simple_card.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 18))
            simple_card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                simple_card,
                text="No modo basico, o perfil escolhido ja aplica as regras essenciais de firewall.",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["muted"],
                wraplength=780,
                justify="left",
            ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 6))
            ctk.CTkLabel(
                simple_card,
                text="Se quiser editar regra por regra, troque o modo da interface para Avancado.",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["primary"],
                wraplength=780,
                justify="left",
            ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 14))
        else:
            # ── Security Options Table (no nested scrollable frame) ─────────────────
            sec_header_frame = ctk.CTkFrame(firewall_card, fg_color="transparent")
            sec_header_frame.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 4))
            sec_header_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                sec_header_frame,
                text="Opcoes de seguranca" + (" — modo Customizado ativo" if custom_mode else ""),
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=COLORS["primary"] if custom_mode else COLORS["text"],
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                sec_header_frame,
                text=(
                    "Checkboxes habilitados: marque ou desmarque cada regra individualmente."
                    if custom_mode else
                    "Nos perfis prontos as opcoes sao definidas automaticamente. Selecione Customizado para editar."
                ),
                font=ctk.CTkFont(size=12),
                text_color=COLORS["muted"],
                wraplength=820,
                justify="left",
            ).grid(row=1, column=0, sticky="w", pady=(2, 10))

            option_table = ctk.CTkFrame(firewall_card, fg_color=COLORS["bg"], corner_radius=16)
            option_table.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 18))
            option_table.grid_columnconfigure(0, weight=1)

            visible_option_names = set(obter_chaves_firewall_por_modo(self.interface_mode_var.get()))
            row = 0
            for categoria in FIREWALL_CATEGORY_ORDER:
                group_options = [
                    (name, data)
                    for name, data in FIREWALL_OPTIONS.items()
                    if data["categoria"] == categoria and name in visible_option_names
                ]
                if not group_options:
                    continue

                ctk.CTkLabel(
                    option_table,
                    text=FIREWALL_CATEGORY_TITLES[categoria],
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=COLORS["primary"],
                ).grid(row=row, column=0, sticky="w", padx=14, pady=(12, 6))
                row += 1

                for name, data in group_options:
                    enabled = self.firewall_option_vars[name].get()
                    disable_for_version = name == "raw_dns_v7" and self.version_var.get() != 7
                    checkbox_state = "normal" if custom_mode and not disable_for_version else "disabled"

                    line = ctk.CTkFrame(option_table, fg_color=COLORS["card"], corner_radius=14)
                    line.grid(row=row, column=0, sticky="ew", padx=6, pady=3)
                    line.grid_columnconfigure(1, weight=1)

                    ctk.CTkCheckBox(
                        line,
                        text="",
                        variable=self.firewall_option_vars[name],
                        state=checkbox_state,
                        command=self._refresh_security_step_if_visible,
                        fg_color=COLORS["primary"],
                        hover_color="#16555D",
                        border_color=COLORS["primary"] if custom_mode else COLORS["muted"],
                        checkmark_color="#FFFFFF",
                    ).grid(row=0, column=0, rowspan=2, padx=(12, 4), pady=10)
                    ctk.CTkLabel(
                        line,
                        text=data["titulo"],
                        font=ctk.CTkFont(size=13, weight="bold"),
                        text_color=COLORS["primary"] if custom_mode and not disable_for_version else COLORS["text"],
                    ).grid(row=0, column=1, sticky="w", padx=8, pady=(10, 2))
                    extra = "Disponivel apenas no RouterOS v7." if disable_for_version else data["descricao"]
                    ctk.CTkLabel(
                        line,
                        text=extra,
                        font=ctk.CTkFont(size=12),
                        text_color=COLORS["muted"],
                        wraplength=600,
                        justify="left",
                        anchor="w",
                    ).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 10))
                    badge_text = "Ativo" if enabled else "Desligado"
                    ctk.CTkLabel(
                        line,
                        text=badge_text,
                        fg_color=COLORS["accent_soft"] if enabled else COLORS["danger_soft"],
                        text_color=COLORS["accent"] if enabled else COLORS["danger"],
                        corner_radius=10,
                        font=ctk.CTkFont(size=11, weight="bold"),
                        padx=12,
                        pady=6,
                    ).grid(row=0, column=2, rowspan=2, padx=(8, 14))
                    row += 1

        # ── Services Card ───────────────────────────────────────────────────────
        service_card = self._section_card(scroll, pady=(16, 0))
        service_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            service_card,
            text="Servicos de gerenciamento",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            service_card,
            text="Habilite apenas os servicos que voce realmente usa para reduzir a superficie de ataque.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

        quick = ctk.CTkFrame(service_card, fg_color="transparent")
        quick.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        quick.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(
            quick,
            text="Usar configuracao sugerida",
            command=self.apply_service_suggestion,
            fg_color=COLORS["primary_soft"],
            hover_color="#CAE6E8",
            text_color=COLORS["primary"],
        ).grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkButton(
            quick,
            text="Habilitar tudo",
            command=self.enable_all_services,
            fg_color=COLORS["warning_soft"],
            hover_color="#FDE6B6",
            text_color=COLORS["warning"],
        ).grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkButton(
            quick,
            text="Desabilitar o inseguro",
            command=self.disable_insecure_services,
            fg_color=COLORS["accent_soft"],
            hover_color="#CFEAD8",
            text_color=COLORS["accent"],
        ).grid(row=0, column=2, sticky="ew", padx=4)

        # Services list (plain frame, no nested scroll)
        svc_table = ctk.CTkFrame(service_card, fg_color=COLORS["bg"], corner_radius=16)
        svc_table.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))
        svc_table.grid_columnconfigure(0, weight=1)

        for row, (name, label, _, suggestion) in enumerate(SERVICOS_PADRAO):
            line = ctk.CTkFrame(svc_table, fg_color=COLORS["card"], corner_radius=14)
            line.grid(row=row, column=0, sticky="ew", padx=6, pady=3)
            line.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                line,
                text=label,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["text"],
            ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
            ctk.CTkLabel(
                line,
                text=suggestion,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["muted"],
                wraplength=560,
                justify="left",
                anchor="w",
            ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

            enabled = self.service_vars[name].get()
            ctk.CTkLabel(
                line,
                text="Ligado" if enabled else "Desligado",
                fg_color=COLORS["accent_soft"] if enabled else COLORS["danger_soft"],
                corner_radius=10,
                text_color=COLORS["accent"] if enabled else COLORS["danger"],
                font=ctk.CTkFont(size=11, weight="bold"),
                padx=12,
                pady=6,
            ).grid(row=0, column=1, rowspan=2, padx=(8, 10))

            ctk.CTkSwitch(
                line,
                text="",
                variable=self.service_vars[name],
                command=self._refresh_security_step_if_visible,
                progress_color=COLORS["primary"],
                button_color=COLORS["primary"],
                button_hover_color=COLORS["primary"],
            ).grid(row=0, column=2, rowspan=2, padx=(0, 14))

        self._render_nav()

    def _render_summary_step(self) -> None:
        self._set_content_header(
            "Revise antes de gerar o script",
            "O preview ja aparece abaixo para voce copiar ou salvar direto.",
        )
        self.script_preview = gerar_script(self._build_config())

        top = self._section_card(self.content_body)
        top.grid_columnconfigure(0, weight=1)
        summary_lines = [
            f"Versao: RouterOS v{self.version_var.get()}",
            f"PPPoE: {'ativado' if self.use_pppoe_var.get() else 'desativado'}",
            f"Rede local: {self._derived_network_text(single_line=True)}",
            f"VLANs: {', '.join(self._enabled_vlan_profile_titles()) if self._enabled_vlan_profile_titles() else 'nenhuma'}",
            f"Firewall: {self._firewall_summary_text(include_options=True)}",
            f"Servicos ligados: {self._enabled_services_text()}",
        ]
        ctk.CTkLabel(
            top,
            text="\n".join(summary_lines),
            justify="left",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=18)

        bottom = self._section_card(self.content_body, pady=(18, 0))
        bottom.grid_rowconfigure(1, weight=1)
        bottom.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bottom,
            text="Preview do script .rsc",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        self.preview_box = ctk.CTkTextbox(
            bottom,
            height=340,
            fg_color=COLORS["bg"],
            border_width=1,
            border_color=COLORS["border"],
            font=ctk.CTkFont(family="Courier", size=12),
        )
        self.preview_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 14))
        self.refresh_preview()

        actions = ctk.CTkFrame(bottom, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        actions.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(
            actions,
            text="Voltar",
            command=self.previous_step,
            fg_color=COLORS["primary_soft"],
            hover_color="#CAE6E8",
            text_color=COLORS["primary"],
        ).grid(row=0, column=0, sticky="ew", padx=4)
        ctk.CTkButton(
            actions,
            text="Gerar configuracao",
            command=self.refresh_preview,
            fg_color=COLORS["primary"],
            hover_color="#16555D",
        ).grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkButton(
            actions,
            text="Copiar script",
            command=self.copy_script,
            fg_color=COLORS["accent"],
            hover_color="#256D46",
        ).grid(row=0, column=2, sticky="ew", padx=4)
        ctk.CTkButton(
            actions,
            text="Salvar .rsc",
            command=self.save_script,
            fg_color=COLORS["warning"],
            hover_color="#BF7A00",
        ).grid(row=0, column=3, sticky="ew", padx=4)

    def _render_nav(self, parent: ctk.CTkBaseClass | None = None) -> None:
        assert self.content_body is not None
        target = parent or self.content_body
        nav = ctk.CTkFrame(target, fg_color="transparent")
        row = self._content_row if parent is not None else 99
        nav.grid(row=row, column=0, sticky="e", pady=(18, 0))
        nav.grid_columnconfigure((0, 1), weight=0)

        if self.current_step != STEP_ORDER[0]:
            ctk.CTkButton(
                nav,
                text="Voltar",
                command=self.previous_step,
                fg_color=COLORS["primary_soft"],
                hover_color="#CAE6E8",
                text_color=COLORS["primary"],
                width=120,
            ).grid(row=0, column=0, padx=(0, 8))

        if self.current_step != STEP_ORDER[-1]:
            ctk.CTkButton(
                nav,
                text="Continuar",
                command=self.next_step,
                fg_color=COLORS["primary"],
                hover_color="#16555D",
                width=140,
            ).grid(row=0, column=1)

    def _set_content_header(self, title: str, subtitle: str) -> None:
        assert self.content_title is not None and self.content_subtitle is not None
        self.content_title.configure(text=title)
        self.content_subtitle.configure(text=subtitle)

    def _section_card(self, parent: ctk.CTkBaseClass, pady: tuple[int, int] = (0, 0)) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS["card"],
            corner_radius=20,
            border_width=1,
            border_color=COLORS["border"],
        )
        card.grid(row=self._content_row, column=0, sticky="ew", pady=pady)
        self._content_row += 1
        return card

    def _choice_card(
        self,
        parent: ctk.CTkBaseClass,
        *,
        row: int,
        column: int,
        title: str,
        description: str,
        selected: bool,
        badge: str,
        badge_color: str,
        badge_text_color: str,
        command,
    ) -> None:
        frame = ctk.CTkFrame(
            parent,
            fg_color=COLORS["primary_soft"] if selected else COLORS["bg"],
            border_width=2 if selected else 1,
            border_color=COLORS["primary"] if selected else COLORS["border"],
            corner_radius=18,
        )
        frame.grid(row=row, column=column, sticky="nsew", padx=8, pady=(0, 18))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text=badge,
            fg_color=badge_color,
            text_color=badge_text_color,
            corner_radius=10,
            font=ctk.CTkFont(size=11, weight="bold"),
            padx=12,
            pady=6,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).grid(row=1, column=0, sticky="w", padx=14)
        ctk.CTkLabel(
            frame,
            text=description,
            justify="left",
            wraplength=220,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["muted"],
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(6, 12))
        ctk.CTkButton(
            frame,
            text="Selecionado" if selected else "Selecionar",
            command=command,
            fg_color=COLORS["primary"] if not selected else COLORS["accent"],
            hover_color="#16555D" if not selected else "#256D46",
        ).grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))

    def _step_hint(self, step: str) -> str:
        hints = {
            "versao": "Escolha v6 ou v7.",
            "internet": "PPPoE e porta WAN.",
            "rede_local": "LAN, DHCP e perfis de VLAN.",
            "seguranca": "Firewall e servicos.",
            "resumo": "Preview do .rsc.",
        }
        return hints[step]

    def _update_step_rail(self) -> None:
        current_index = STEP_ORDER.index(self.current_step)
        for index, step in enumerate(STEP_ORDER):
            label, number = self.step_labels[step]
            if index == current_index:
                label.configure(text_color=COLORS["primary"])
                number.configure(fg_color=COLORS["primary"], text_color="#FFFFFF")
            elif index < current_index:
                label.configure(text_color=COLORS["accent"])
                number.configure(fg_color=COLORS["accent_soft"], text_color=COLORS["accent"])
            else:
                label.configure(text_color=COLORS["text"])
                number.configure(fg_color=COLORS["primary_soft"], text_color=COLORS["primary"])

    def _error_label(
        self,
        parent: ctk.CTkBaseClass,
        key: str,
        *,
        row: int,
        column: int,
        columnspan: int,
    ) -> None:
        message = self.inline_errors.get(key, "")
        ctk.CTkLabel(
            parent,
            text=message,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["danger"],
        ).grid(row=row, column=column, columnspan=columnspan, sticky="w", padx=18, pady=(0, 6))

    def _selected_mask_value(self) -> str:
        return self.mask_var.get().split(" ", 1)[0]

    def _bind_summary_var(self, variable: tk.Variable) -> None:
        variable.trace_add("write", lambda *_: self.refresh_summary())

    def _build_vlan_vars(self, item: dict[str, str | bool | int]) -> dict[str, tk.Variable]:
        bandwidth = str(item["limite_banda"]).strip()
        return {
            "title": tk.StringVar(value=str(item["titulo"])),
            "enabled": tk.BooleanVar(value=bool(item["habilitada"])),
            "vlan_id": tk.StringVar(value=str(item["vlan_id"])),
            "network": tk.StringVar(value=str(item["rede"])),
            "isolated": tk.BooleanVar(value=bool(item["isolada"])),
            "internet_only": tk.BooleanVar(value=bool(item["internet_only"])),
            "access_vlan": tk.StringVar(value=self._vlan_access_choice_label(str(item["access_vlan"]))),
            "dhcp": tk.BooleanVar(value=bool(item["dhcp_proprio"])),
            "dns": tk.BooleanVar(value=bool(item["dns_proprio"])),
            "bandwidth": tk.StringVar(value=bandwidth),
            "bandwidth_preset": tk.StringVar(value=self._bandwidth_preset_for_value(bandwidth)),
        }

    def _register_vlan_vars(self, chave: str, vars_map: dict[str, tk.Variable]) -> None:
        for variable in vars_map.values():
            self._bind_summary_var(variable)
        vars_map["bandwidth"].trace_add("write", lambda *_: self._sync_vlan_bandwidth_preset(chave))

    def _bandwidth_preset_for_value(self, value: str) -> str:
        value = value.strip()
        if not value:
            return "Sem limite"
        if value in BANDWIDTH_PRESET_OPTIONS:
            return value
        return "Customizado"

    def _set_vlan_bandwidth_preset(self, chave: str, preset: str) -> None:
        vars_map = self.vlan_profile_vars.get(chave)
        if vars_map is None:
            return
        vars_map["bandwidth_preset"].set(preset)
        if preset == "Sem limite":
            vars_map["bandwidth"].set("")
        elif preset != "Customizado":
            vars_map["bandwidth"].set(preset)
        self.refresh_summary()

    def _sync_vlan_bandwidth_preset(self, chave: str) -> None:
        vars_map = self.vlan_profile_vars.get(chave)
        if vars_map is None:
            return
        preset = self._bandwidth_preset_for_value(str(vars_map["bandwidth"].get()))
        if vars_map["bandwidth_preset"].get() != preset:
            vars_map["bandwidth_preset"].set(preset)

    def _next_custom_vlan_defaults(self) -> tuple[int, str]:
        used_ids = {
            int(str(values["vlan_id"].get()).strip())
            for values in self.vlan_profile_vars.values()
            if str(values["vlan_id"].get()).strip().isdigit()
        }
        used_networks = {
            str(values["network"].get()).strip()
            for values in self.vlan_profile_vars.values()
            if str(values["network"].get()).strip()
        }

        for candidate in range(30, 255):
            network = f"192.168.{candidate}.0/24"
            if candidate not in used_ids and network not in used_networks:
                return candidate, network

        fallback_id = 100
        while fallback_id in used_ids and fallback_id <= 4094:
            fallback_id += 1
        return fallback_id, f"10.{min(fallback_id, 254)}.0.0/24"

    def _add_custom_vlan(self) -> None:
        self.custom_vlan_index += 1
        chave = f"custom_{self.custom_vlan_index}"
        vlan_id, network = self._next_custom_vlan_defaults()
        item = {
            "chave": chave,
            "titulo": f"VLAN extra {self.custom_vlan_index}",
            "descricao": "VLAN adicional criada manualmente para separar outro ambiente ou servico.",
            "habilitada": True,
            "vlan_id": vlan_id,
            "rede": network,
            "isolada": False,
            "internet_only": False,
            "access_vlan": "",
            "dhcp_proprio": True,
            "dns_proprio": False,
            "limite_banda": "",
        }
        vars_map = self._build_vlan_vars(item)
        self.vlan_profile_vars[chave] = vars_map
        self._register_vlan_vars(chave, vars_map)
        self.custom_vlan_keys.append(chave)
        self._refresh_current_step_and_summary()

    def _remove_custom_vlan(self, chave: str) -> None:
        if chave not in self.custom_vlan_keys:
            return
        self.custom_vlan_keys.remove(chave)
        self.vlan_profile_vars.pop(chave, None)
        for values in self.vlan_profile_vars.values():
            if self._vlan_access_key(str(values["access_vlan"].get())) == chave:
                values["access_vlan"].set("Nenhuma")
        self._refresh_current_step_and_summary()

    def _collect_vlan_profiles(self) -> list[dict[str, str | bool | int]]:
        return [
            {
                "chave": chave,
                "titulo": str(values["title"].get()).strip(),
                "habilitada": values["enabled"].get(),
                "vlan_id": values["vlan_id"].get(),
                "rede": values["network"].get(),
                "isolada": values["isolated"].get(),
                "internet_only": values["internet_only"].get(),
                "access_vlan": self._vlan_access_key(values["access_vlan"].get()),
                "dhcp_proprio": values["dhcp"].get(),
                "dns_proprio": values["dns"].get(),
                "limite_banda": values["bandwidth"].get(),
            }
            for chave, values in self.vlan_profile_vars.items()
        ]

    def _enabled_vlan_profile_titles(self) -> list[str]:
        return [
            self._vlan_title_for_key(chave)
            for chave, values in self.vlan_profile_vars.items()
            if values["enabled"].get()
        ]

    def _vlan_title_for_key(self, chave: str) -> str:
        values = self.vlan_profile_vars.get(chave)
        if values is not None:
            titulo = str(values["title"].get()).strip()
            if titulo:
                return titulo
        if chave in VLAN_PROFILE_PRESETS:
            return str(VLAN_PROFILE_PRESETS[chave]["titulo"])
        return "VLAN extra"

    def _vlan_description_for_key(self, chave: str) -> str:
        if chave in VLAN_PROFILE_PRESETS:
            return str(VLAN_PROFILE_PRESETS[chave]["descricao"])
        return "Use essa VLAN para criar uma rede adicional do seu jeito, sem depender dos perfis prontos."

    def _vlan_access_choice_label(self, chave: str) -> str:
        if not chave:
            return "Nenhuma"
        vlan_id = ""
        values = self.vlan_profile_vars.get(chave)
        if values is not None:
            vlan_id = str(values["vlan_id"].get()).strip()
        elif chave in VLAN_PROFILE_PRESETS:
            vlan_id = str(VLAN_PROFILE_PRESETS[chave]["vlan_id"])
        suffix = f" (VLAN {vlan_id})" if vlan_id else ""
        return f"{self._vlan_title_for_key(chave)}{suffix}"

    def _available_vlan_access_labels(self, origem: str) -> list[str]:
        options = ["Nenhuma"]
        for chave in list(DEFAULT_VLAN_KEYS) + list(self.custom_vlan_keys):
            if chave == origem:
                continue
            values = self.vlan_profile_vars.get(chave)
            if values is None or not values["enabled"].get():
                continue
            options.append(self._vlan_access_choice_label(chave))
        return options

    def _vlan_access_key(self, label: str) -> str:
        if not label or label == "Nenhuma":
            return ""
        for chave in self.vlan_profile_vars:
            if self._vlan_access_choice_label(chave) == label:
                return chave
        return ""

    def _enabled_firewall_option_titles(self) -> list[str]:
        return [
            data["titulo"]
            for name, data in FIREWALL_OPTIONS.items()
            if self.firewall_option_vars[name].get()
        ]

    def _firewall_summary_text(self, *, include_options: bool = False) -> str:
        profile = self.firewall_var.get()
        title = PERFIS_FIREWALL[profile]["titulo"]
        if profile != "custom":
            return title

        enabled = self._enabled_firewall_option_titles()
        if not include_options:
            return f"{title} ({len(enabled)} opcoes)"
        return f"{title} ({len(enabled)} opcoes: {', '.join(enabled)})"

    def _derived_network_text(self, *, single_line: bool = False) -> str:
        try:
            rede = parse_rede_lan(self.network_var.get(), self._selected_mask_value())
        except ValueError as exc:
            return str(exc)

        final = f"Rede final: {rede.network_address}/{rede.prefixlen}"
        gateway = f"Gateway sugerido: {rede.network_address + 1}"
        return f"{final} | {gateway}" if single_line else f"{final}\n{gateway}"

    def _enabled_services_text(self) -> str:
        ativos = [label for name, label, _, _ in SERVICOS_PADRAO if self.service_vars[name].get()]
        return ", ".join(ativos) if ativos else "nenhum"


def launch() -> None:
    app = MikrotikGeneratorApp()
    app.mainloop()
