from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from assistente_config_mikrotik import (
    FIREWALL_OPTIONS,
    PERFIS_FIREWALL,
    SERVICOS_PADRAO,
    criar_configuracao,
    gerar_script,
    normalizar_interfaces_lan,
    obter_opcoes_firewall_padrao,
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
        self.wan_var = tk.StringVar(value="ether1")
        self.lan_var = tk.StringVar(value="ether2,ether3,ether4,ether5")
        self.network_var = tk.StringVar(value="192.168.10.0")
        self.mask_var = tk.StringVar(value=MASK_OPTIONS[0])
        self.dhcp_var = tk.BooleanVar(value=True)
        self.firewall_var = tk.StringVar(value="medium")
        self.password_visible = False

        self.firewall_option_vars = {
            name: tk.BooleanVar(value=enabled)
            for name, enabled in obter_opcoes_firewall_padrao("medium", self.version_var.get()).items()
        }
        self.service_vars = {
            name: tk.BooleanVar(value=default)
            for name, default in obter_servicos_padrao().items()
        }

        self.step_labels: dict[str, tuple[ctk.CTkLabel, ctk.CTkLabel]] = {}
        self.summary_value_labels: dict[str, ctk.CTkLabel] = {}
        self.summary_services_box: ctk.CTkTextbox | None = None
        self.content_title: ctk.CTkLabel | None = None
        self.content_subtitle: ctk.CTkLabel | None = None
        self.content_body: ctk.CTkFrame | None = None
        self.preview_box: ctk.CTkTextbox | None = None

        self._build_layout()
        self._bind_live_updates()
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
            text="Minha sugestao geral: RouterOS v7, firewall medio e so os servicos que voce realmente usa.",
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
            variable.trace_add("write", lambda *_: self.refresh_summary())

        self.version_var.trace_add("write", lambda *_: self._handle_version_change())

    def show_step(self, step: str) -> None:
        self.current_step = step
        self.step_title_label.configure(text=STEP_TITLES[step])
        self._update_step_rail()
        self._render_current_step()
        self.refresh_summary()

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
            rede=self.network_var.get(),
            mascara=self._selected_mask_value(),
            criar_dhcp=self.dhcp_var.get(),
            perfil_firewall=self.firewall_var.get(),
            servicos={name: variable.get() for name, variable in self.service_vars.items()},
            interface_wan=self.wan_var.get(),
            interfaces_lan=self.lan_var.get(),
            firewall_opcoes={name: variable.get() for name, variable in self.firewall_option_vars.items()},
        )

    def refresh_summary(self) -> None:
        self.summary_value_labels["Versao"].configure(
            text=f"RouterOS v{self.version_var.get()}"
        )

        pppoe_text = "Ativado" if self.use_pppoe_var.get() else "Desativado"
        if self.use_pppoe_var.get() and self.pppoe_user_var.get().strip():
            pppoe_text += f"\nUsuario: {self.pppoe_user_var.get().strip()}"
        self.summary_value_labels["PPPoE"].configure(text=pppoe_text)

        try:
            rede = parse_rede_lan(self.network_var.get(), self._selected_mask_value())
            lan_text = f"{rede.network_address}/{rede.prefixlen}\nGateway sugerido: {rede.network_address + 1}"
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

    def _handle_version_change(self) -> None:
        if self.identity_var.get().strip() in {"MikroTik-v6", "MikroTik-v7", ""}:
            self.identity_var.set(f"MikroTik-v{self.version_var.get()}")

        if self.firewall_var.get() != "custom":
            defaults = obter_opcoes_firewall_padrao(self.firewall_var.get(), self.version_var.get())
            for name, value in defaults.items():
                self.firewall_option_vars[name].set(value)
        elif self.version_var.get() != 7:
            self.firewall_option_vars["raw_dns_v7"].set(False)

        self._refresh_current_step_if_needed({"versao", "seguranca"})

    def _set_firewall_profile(self, profile: str) -> None:
        current = self.firewall_var.get()
        if current != profile:
            self.firewall_var.set(profile)

        if profile == "custom":
            # Custom: start from medium defaults so user has a meaningful baseline to edit
            if current != "custom":
                defaults = obter_opcoes_firewall_padrao("medium", self.version_var.get())
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
        card = self._section_card(self.content_body)
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

        self._render_nav()

    def _render_lan_step(self) -> None:
        self._set_content_header(
            "Configuracao da rede local",
            "Sugestao: 192.168.10.0 /24 para redes pequenas e medias.",
        )
        card = self._section_card(self.content_body)
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

        self._render_nav()

    def _render_security_step(self) -> None:
        self._set_content_header(
            "Seguranca e Firewall",
            "Escolha um perfil de firewall e ajuste os servicos de gerenciamento.",
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

        profile_table = ctk.CTkFrame(firewall_card, fg_color=COLORS["bg"], corner_radius=16)
        profile_table.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
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

        for row, profile in enumerate(["basic", "medium", "advanced", "custom"], start=1):
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

        # ── Security Options Table (no nested scrollable frame) ─────────────────
        custom_mode = self.firewall_var.get() == "custom"

        sec_header_frame = ctk.CTkFrame(firewall_card, fg_color="transparent")
        sec_header_frame.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 4))
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
        option_table.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 18))
        option_table.grid_columnconfigure(0, weight=1)

        for row, (name, data) in enumerate(FIREWALL_OPTIONS.items()):
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

    def _render_nav(self) -> None:
        assert self.content_body is not None
        nav = ctk.CTkFrame(self.content_body, fg_color="transparent")
        nav.grid(row=99, column=0, sticky="e", pady=(18, 0))
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
            "rede_local": "LAN, mascara e DHCP.",
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
