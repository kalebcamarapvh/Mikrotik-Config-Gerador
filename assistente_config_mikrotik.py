from __future__ import annotations

from dataclasses import dataclass, field
from getpass import getpass
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
import sys


SERVICOS_PADRAO = [
    (
        "winbox",
        "Winbox",
        True,
        "Sugestao: SIM. Normalmente e o jeito mais pratico de administrar o MikroTik.",
    ),
    (
        "ssh",
        "SSH",
        True,
        "Sugestao: SIM se voce usa terminal. Se nao usa, pode desligar.",
    ),
    (
        "www",
        "WebFig HTTP",
        False,
        "Sugestao: NAO. HTTP exposto nao e uma boa pratica.",
    ),
    (
        "www-ssl",
        "WebFig HTTPS",
        False,
        "Sugestao: NAO por padrao. Ligue so se voce realmente usar o acesso web.",
    ),
    (
        "api",
        "API",
        False,
        "Sugestao: NAO. Ligue apenas se algum sistema depender disso.",
    ),
    (
        "api-ssl",
        "API-SSL",
        False,
        "Sugestao: NAO por padrao. Ligue so se voce tiver uma integracao que precise.",
    ),
    (
        "ftp",
        "FTP",
        False,
        "Sugestao: NAO. Em geral nao vale a pena deixar ligado.",
    ),
    (
        "telnet",
        "Telnet",
        False,
        "Sugestao: NAO. E antigo e inseguro.",
    ),
]

FIREWALL_CATEGORY_ORDER = ["input", "forward", "output", "support"]
FIREWALL_CATEGORY_TITLES = {
    "input": "Input",
    "forward": "Forward",
    "output": "Output",
    "support": "Apoio",
}
FIREWALL_PROFILE_ORDER = ["basic", "recommended", "advanced", "custom"]
FIREWALL_PROFILE_VISIBILITY = {
    "basic": {"basic", "recommended"},
    "advanced": {"basic", "recommended", "advanced", "custom"},
}
DNS_PROFILE_ORDER = ["compatibility", "malware", "family", "custom"]
DNS_PROFILES = {
    "compatibility": {
        "titulo": "Melhor compatibilidade",
        "descricao": "Google e Cloudflare para boa compatibilidade no dia a dia.",
        "primario": "8.8.8.8",
        "secundario": "1.1.1.1",
    },
    "malware": {
        "titulo": "Contra malwares",
        "descricao": "Quad9 com Cloudflare para priorizar bloqueio de dominios maliciosos.",
        "primario": "9.9.9.9",
        "secundario": "1.1.1.1",
    },
    "family": {
        "titulo": "Filtro de conteudo",
        "descricao": "OpenDNS Family para filtragem basica de conteudo.",
        "primario": "208.67.222.123",
        "secundario": "208.67.220.123",
    },
    "custom": {
        "titulo": "Customizado",
        "descricao": "Permite definir manualmente DNS primario e secundario.",
        "primario": "",
        "secundario": "",
    },
}
VLAN_PROFILE_ORDER = ["main", "guests", "iot", "cctv", "servers", "management"]


def eh_chave_vlan_customizada(chave: str) -> bool:
    return chave.startswith("custom_")


def obter_dados_vlan(chave: str, bruto: dict[str, str | bool | int] | None = None) -> dict[str, str | bool | int]:
    if chave in VLAN_PROFILE_PRESETS:
        return VLAN_PROFILE_PRESETS[chave]
    if eh_chave_vlan_customizada(chave):
        titulo = "VLAN extra"
        if bruto is not None:
            titulo = str(bruto.get("titulo", titulo)).strip() or titulo
        return {
            "titulo": titulo,
            "descricao": "VLAN adicional criada manualmente.",
            "vlan_id": 30,
            "rede": "192.168.30.0/24",
            "isolada": False,
            "internet_only": False,
            "access_vlan": "",
            "dhcp_proprio": True,
            "dns_proprio": False,
            "limite_banda": "",
        }
    raise ValueError("Perfil de VLAN invalido.")
VLAN_PROFILE_PRESETS = {
    "main": {
        "titulo": "Rede principal",
        "descricao": "Rede principal para usuarios e equipamentos gerais.",
        "vlan_id": 10,
        "rede": "192.168.10.0/24",
        "isolada": False,
        "internet_only": False,
        "access_vlan": "",
        "dhcp_proprio": True,
        "dns_proprio": True,
        "limite_banda": "",
    },
    "guests": {
        "titulo": "Visitantes",
        "descricao": "Rede separada para convidados e dispositivos temporarios.",
        "vlan_id": 20,
        "rede": "192.168.20.0/24",
        "isolada": True,
        "internet_only": True,
        "access_vlan": "",
        "dhcp_proprio": True,
        "dns_proprio": True,
        "limite_banda": "20M/20M",
    },
    "iot": {
        "titulo": "IoT",
        "descricao": "Segmento para automacao, cameras pequenas e dispositivos inteligentes.",
        "vlan_id": 30,
        "rede": "192.168.30.0/24",
        "isolada": True,
        "internet_only": True,
        "access_vlan": "",
        "dhcp_proprio": True,
        "dns_proprio": False,
        "limite_banda": "",
    },
    "cctv": {
        "titulo": "CFTV",
        "descricao": "Segmento para gravadores, NVRs e cameras IP.",
        "vlan_id": 40,
        "rede": "192.168.40.0/24",
        "isolada": True,
        "internet_only": False,
        "access_vlan": "management",
        "dhcp_proprio": True,
        "dns_proprio": False,
        "limite_banda": "",
    },
    "servers": {
        "titulo": "Servidores",
        "descricao": "Rede para workloads internos, aplicacoes e servicos dedicados.",
        "vlan_id": 50,
        "rede": "192.168.50.0/24",
        "isolada": False,
        "internet_only": False,
        "access_vlan": "management",
        "dhcp_proprio": False,
        "dns_proprio": False,
        "limite_banda": "",
    },
    "management": {
        "titulo": "Gestao/TI",
        "descricao": "Rede administrativa para equipe tecnica e gerenciamento.",
        "vlan_id": 99,
        "rede": "192.168.99.0/24",
        "isolada": False,
        "internet_only": False,
        "access_vlan": "servers",
        "dhcp_proprio": True,
        "dns_proprio": True,
        "limite_banda": "",
    },
}

PERFIS_FIREWALL = {
    "basic": {
        "titulo": "Basico",
        "descricao": "Boa base para casa e escritorio pequeno.",
        "sugestao": "Sugestao: use BASICO se voce quer algo simples e seguro sem exagero.",
        "quando_usar": "Instalacao simples e mais compativel.",
    },
    "recommended": {
        "titulo": "Recomendado",
        "descricao": "Equilibrio entre compatibilidade, bloqueio WAN e higiene entre cadeias.",
        "sugestao": "Sugestao: use RECOMENDADO na maioria dos casos. E o melhor equilibrio.",
        "quando_usar": "Melhor equilibrio para a maioria dos cenarios.",
    },
    "advanced": {
        "titulo": "Avancado",
        "descricao": "Mais visibilidade, mais endurecimento e regra raw no RouterOS v7.",
        "sugestao": "Sugestao: use AVANCADO se voce ja sabe o que quer e aceita mais rigidez.",
        "quando_usar": "Quando voce quer endurecer mais as regras.",
    },
    "custom": {
        "titulo": "Customizado",
        "descricao": "Voce escolhe manualmente quais opcoes de seguranca entram no script.",
        "sugestao": "Sugestao: use CUSTOMIZADO quando quiser ajustar regra por regra.",
        "quando_usar": "Quando precisar escolher cada opcao manualmente.",
    },
}

FIREWALL_OPTIONS = {
    "accept_established": {
        "titulo": "Aceitar conexoes estabelecidas",
        "descricao": "Mantem funcionando o trafego ja iniciado e respostas de conexoes validas.",
        "categoria": "input",
        "modo_minimo": "basic",
    },
    "drop_invalid": {
        "titulo": "Descartar conexoes invalidas",
        "descricao": "Remove pacotes quebrados ou fora de estado para limpar ruido.",
        "categoria": "input",
        "modo_minimo": "basic",
    },
    "accept_icmp": {
        "titulo": "Permitir ICMP (ping)",
        "descricao": "Facilita testes de rede e diagnostico basico.",
        "categoria": "input",
        "modo_minimo": "basic",
    },
    "allow_lan_input": {
        "titulo": "Permitir acesso ao roteador pela LAN",
        "descricao": "Autoriza gerenciamento do MikroTik a partir da rede local.",
        "categoria": "input",
        "modo_minimo": "basic",
    },
    "drop_wan_input": {
        "titulo": "Bloquear acesso ao roteador pela WAN",
        "descricao": "Impede tentativas diretas da internet contra o proprio roteador.",
        "categoria": "input",
        "modo_minimo": "basic",
    },
    "output_established": {
        "titulo": "Aceitar output estabelecido",
        "descricao": "Mantem respostas do proprio roteador fluindo sem quebrar sessoes validas.",
        "categoria": "output",
        "modo_minimo": "advanced",
    },
    "drop_output_invalid": {
        "titulo": "Descartar output invalido",
        "descricao": "Remove trafego inconsistente originado localmente no roteador.",
        "categoria": "output",
        "modo_minimo": "advanced",
    },
    "forward_established": {
        "titulo": "Permitir forward estabelecido",
        "descricao": "Mantem o trafego ja em andamento entre LAN e internet.",
        "categoria": "forward",
        "modo_minimo": "basic",
    },
    "drop_forward_invalid": {
        "titulo": "Descartar forward invalido",
        "descricao": "Elimina pacotes de encaminhamento inconsistentes.",
        "categoria": "forward",
        "modo_minimo": "basic",
    },
    "allow_lan_to_wan": {
        "titulo": "Permitir LAN para internet",
        "descricao": "Libera a saida da rede local para a WAN.",
        "categoria": "forward",
        "modo_minimo": "basic",
    },
    "allow_dstnat": {
        "titulo": "Permitir trafego encaminhado (dstnat)",
        "descricao": "Mantem redirecionamentos de porta funcionando quando existirem.",
        "categoria": "forward",
        "modo_minimo": "basic",
    },
    "drop_new_wan_forward": {
        "titulo": "Bloquear novas conexoes vindas da WAN",
        "descricao": "Evita que trafego novo da internet entre na LAN sem regra explicita.",
        "categoria": "forward",
        "modo_minimo": "basic",
    },
    "nat_masquerade": {
        "titulo": "Aplicar NAT masquerade",
        "descricao": "Permite que a rede local navegue usando o IP da WAN.",
        "categoria": "support",
        "modo_minimo": "basic",
    },
    "port_scan": {
        "titulo": "Bloquear port scan",
        "descricao": "Detecta sondagens simples de portas na interface WAN.",
        "categoria": "input",
        "modo_minimo": "advanced",
    },
    "ssh_bruteforce": {
        "titulo": "Proteger SSH contra brute force",
        "descricao": "Bloqueia tentativas repetidas no servico SSH.",
        "categoria": "input",
        "modo_minimo": "advanced",
    },
    "block_dns_wan": {
        "titulo": "Bloquear DNS vindo da WAN",
        "descricao": "Evita uso indevido do roteador como resolvedor exposto.",
        "categoria": "input",
        "modo_minimo": "advanced",
    },
    "log_wan_input": {
        "titulo": "Registrar tentativas na WAN",
        "descricao": "Gera logs de acesso ao roteador vindo da internet.",
        "categoria": "input",
        "modo_minimo": "advanced",
    },
    "log_new_wan_forward": {
        "titulo": "Registrar novas conexoes WAN para frente",
        "descricao": "Ajuda a auditar tentativas novas de trafego vindo da WAN.",
        "categoria": "forward",
        "modo_minimo": "advanced",
    },
    "raw_dns_v7": {
        "titulo": "Bloqueio raw de DNS na WAN (v7)",
        "descricao": "Usa raw table no RouterOS v7 para derrubar DNS indesejado cedo.",
        "categoria": "support",
        "modo_minimo": "advanced",
    },
}


def normalizar_perfil_firewall(perfil: str) -> str:
    if perfil == "medium":
        return "recommended"
    return perfil


def obter_chaves_firewall_por_modo(modo_interface: str) -> list[str]:
    if modo_interface == "advanced":
        return list(FIREWALL_OPTIONS.keys())
    return [
        nome
        for nome, dados in FIREWALL_OPTIONS.items()
        if dados.get("modo_minimo", "basic") == "basic"
    ]


def obter_perfis_firewall_por_modo(modo_interface: str) -> list[str]:
    return [
        perfil
        for perfil in FIREWALL_PROFILE_ORDER
        if perfil in FIREWALL_PROFILE_VISIBILITY.get(modo_interface, FIREWALL_PROFILE_VISIBILITY["basic"])
    ]


def normalizar_perfil_dns(perfil: str) -> str:
    if perfil not in DNS_PROFILES:
        return "compatibility"
    return perfil


@dataclass
class ConfiguracaoAssistente:
    versao_routeros: int
    identidade: str
    usar_pppoe: bool
    pppoe_usuario: str
    pppoe_senha: str
    dns_profile: str
    dns_primario: str
    dns_secundario: str
    rede_lan: IPv4Network
    criar_dhcp: bool
    perfil_firewall: str
    firewall_opcoes: dict[str, bool]
    servicos: dict[str, bool]
    interface_wan: str
    interfaces_lan: list[str]
    vlan_perfis: list["VLANPerfilConfig"] = field(default_factory=list)

    @property
    def bridge_name(self) -> str:
        return "bridge-lan"

    @property
    def interface_internet(self) -> str:
        if self.usar_pppoe:
            return "pppoe-out1"
        return self.interface_wan

    @property
    def dns_servers(self) -> list[str]:
        return [server for server in [self.dns_primario, self.dns_secundario] if server]

    @property
    def prefixo(self) -> int:
        return self.rede_lan.prefixlen

    @property
    def ip_lan_router(self) -> IPv4Address:
        return self.rede_lan.network_address + 1

    @property
    def pool_inicio(self) -> IPv4Address:
        inicio_preferido = self.rede_lan.network_address + 10
        minimo = self.rede_lan.network_address + 2
        if int(inicio_preferido) >= int(self.pool_fim):
            return minimo
        return inicio_preferido

    @property
    def pool_fim(self) -> IPv4Address:
        return self.rede_lan.broadcast_address - 1


@dataclass
class VLANPerfilConfig:
    chave: str
    titulo: str
    habilitada: bool
    vlan_id: int
    rede: IPv4Network
    isolada: bool
    internet_only: bool
    access_vlan: str
    dhcp_proprio: bool
    dns_proprio: bool
    limite_banda: str = ""

    @property
    def nome_slug(self) -> str:
        return self.titulo.lower().replace("/", "-").replace(" ", "-")

    @property
    def interface_name(self) -> str:
        return f"vlan{self.vlan_id}-{self.nome_slug}"

    @property
    def gateway_ip(self) -> IPv4Address:
        return self.rede.network_address + 1

    @property
    def pool_inicio(self) -> IPv4Address:
        inicio_preferido = self.rede.network_address + 10
        minimo = self.rede.network_address + 2
        if int(inicio_preferido) >= int(self.pool_fim):
            return minimo
        return inicio_preferido

    @property
    def pool_fim(self) -> IPv4Address:
        return self.rede.broadcast_address - 1

    @property
    def list_name(self) -> str:
        return f"VLAN-{self.titulo.upper().replace('/', '-').replace(' ', '-')}"


def obter_servicos_padrao() -> dict[str, bool]:
    return {nome: padrao for nome, _, padrao, _ in SERVICOS_PADRAO}


def obter_opcoes_firewall_padrao(perfil: str, versao_routeros: int) -> dict[str, bool]:
    perfil = normalizar_perfil_firewall(perfil)
    if perfil not in PERFIS_FIREWALL:
        raise ValueError("Escolha um perfil de firewall valido.")

    opcoes = {nome: False for nome in FIREWALL_OPTIONS}

    perfis = {
        "basic": {
            "accept_established",
            "drop_invalid",
            "accept_icmp",
            "allow_lan_input",
            "drop_wan_input",
            "forward_established",
            "drop_forward_invalid",
            "allow_lan_to_wan",
            "allow_dstnat",
            "drop_new_wan_forward",
            "nat_masquerade",
        },
        "recommended": {
            "accept_established",
            "drop_invalid",
            "accept_icmp",
            "allow_lan_input",
            "drop_wan_input",
            "forward_established",
            "drop_forward_invalid",
            "allow_lan_to_wan",
            "allow_dstnat",
            "drop_new_wan_forward",
            "nat_masquerade",
            "port_scan",
            "ssh_bruteforce",
            "block_dns_wan",
            "output_established",
            "drop_output_invalid",
        },
        "advanced": {
            "accept_established",
            "drop_invalid",
            "accept_icmp",
            "allow_lan_input",
            "drop_wan_input",
            "forward_established",
            "drop_forward_invalid",
            "allow_lan_to_wan",
            "allow_dstnat",
            "drop_new_wan_forward",
            "nat_masquerade",
            "port_scan",
            "ssh_bruteforce",
            "block_dns_wan",
            "output_established",
            "drop_output_invalid",
            "log_wan_input",
            "log_new_wan_forward",
        },
    }

    ativos = set(perfis["basic"])
    if perfil in {"recommended", "advanced", "custom"}:
        ativos = set(perfis["recommended"])
    if perfil == "advanced":
        ativos = set(perfis["advanced"])
    if perfil == "custom":
        ativos = set(perfis["recommended"])
    if perfil == "advanced" and versao_routeros == 7:
        ativos.add("raw_dns_v7")

    for nome in ativos:
        opcoes[nome] = True

    return opcoes


def normalizar_opcoes_firewall(
    perfil_firewall: str,
    versao_routeros: int,
    firewall_opcoes: dict[str, bool] | None = None,
) -> dict[str, bool]:
    perfil_firewall = normalizar_perfil_firewall(perfil_firewall)
    opcoes = obter_opcoes_firewall_padrao(perfil_firewall, versao_routeros)
    if firewall_opcoes:
        for nome, valor in firewall_opcoes.items():
            if nome in opcoes:
                opcoes[nome] = bool(valor)

    if versao_routeros != 7:
        opcoes["raw_dns_v7"] = False

    return opcoes


def parse_rede_lan(rede: str, mascara: str) -> IPv4Network:
    try:
        rede_lan = IPv4Network(f"{rede.strip()}/{mascara.strip()}", strict=True)
    except ValueError as exc:
        raise ValueError(f"Rede invalida: {exc}") from exc

    if rede_lan.prefixlen > 29:
        raise ValueError("Rede muito pequena. Use pelo menos uma rede /29.")

    return rede_lan


def normalizar_interfaces_lan(valor: str | list[str]) -> list[str]:
    if isinstance(valor, str):
        itens = [item.strip() for item in valor.split(",") if item.strip()]
    else:
        itens = [item.strip() for item in valor if item.strip()]

    if not itens:
        raise ValueError("Informe pelo menos uma interface LAN.")

    return itens


def obter_perfis_vlan_padrao() -> list[dict[str, str | bool | int]]:
    perfis: list[dict[str, str | bool | int]] = []
    for chave in VLAN_PROFILE_ORDER:
        dados = VLAN_PROFILE_PRESETS[chave]
        perfis.append(
            {
                "chave": chave,
                "titulo": str(dados["titulo"]),
                "descricao": str(dados["descricao"]),
                "habilitada": False,
                "vlan_id": int(dados["vlan_id"]),
                "rede": str(dados["rede"]),
                "isolada": bool(dados["isolada"]),
                "internet_only": bool(dados["internet_only"]),
                "access_vlan": str(dados["access_vlan"]),
                "dhcp_proprio": bool(dados["dhcp_proprio"]),
                "dns_proprio": bool(dados["dns_proprio"]),
                "limite_banda": str(dados["limite_banda"]),
            }
        )
    return perfis


def normalizar_perfis_vlan(
    vlan_perfis: list[dict[str, str | bool | int]] | None,
    rede_lan_principal: IPv4Network,
) -> list[VLANPerfilConfig]:
    if not vlan_perfis:
        return []

    perfis_normalizados: list[VLANPerfilConfig] = []
    vlan_ids: set[int] = set()
    redes: set[str] = {str(rede_lan_principal)}
    titulos_por_chave: dict[str, str] = {}

    for bruto in vlan_perfis:
        chave = str(bruto.get("chave", "")).strip().lower()
        dados_vlan = obter_dados_vlan(chave, bruto)
        titulo = str(bruto.get("titulo", dados_vlan["titulo"])).strip() or str(dados_vlan["titulo"])
        titulos_por_chave[chave] = titulo

    for bruto in vlan_perfis:
        chave = str(bruto.get("chave", "")).strip().lower()
        dados_vlan = obter_dados_vlan(chave, bruto)

        if not bool(bruto.get("habilitada")):
            continue

        titulo = titulos_por_chave[chave]
        vlan_id = int(bruto.get("vlan_id", dados_vlan["vlan_id"]))
        if not 1 <= vlan_id <= 4094:
            raise ValueError(f"VLAN ID invalida para {titulo}. Use um valor entre 1 e 4094.")
        if vlan_id in vlan_ids:
            raise ValueError(f"VLAN ID duplicada: {vlan_id}.")

        rede = rede_lan_principal if chave == "main" else parse_rede_vlan(str(bruto.get("rede", dados_vlan["rede"])))
        if chave != "main" and str(rede) in redes:
            raise ValueError(f"A rede {rede} esta duplicada entre LAN/VLANs.")

        access_vlan = str(bruto.get("access_vlan", "")).strip().lower()
        if access_vlan and access_vlan not in titulos_por_chave:
            raise ValueError(f"VLAN de acesso invalida para {titulo}.")
        if access_vlan == chave:
            raise ValueError(f"{titulo} nao pode apontar acesso para ela mesma.")

        perfil = VLANPerfilConfig(
            chave=chave,
            titulo=str(titulo),
            habilitada=True,
            vlan_id=vlan_id,
            rede=rede,
            isolada=bool(bruto.get("isolada")),
            internet_only=bool(bruto.get("internet_only")),
            access_vlan=access_vlan,
            dhcp_proprio=bool(bruto.get("dhcp_proprio")),
            dns_proprio=bool(bruto.get("dns_proprio")),
            limite_banda=str(bruto.get("limite_banda", "")).strip(),
        )
        perfis_normalizados.append(perfil)
        vlan_ids.add(vlan_id)
        if chave != "main":
            redes.add(str(rede))

    chaves_habilitadas = {perfil.chave for perfil in perfis_normalizados}
    for perfil in perfis_normalizados:
        if perfil.access_vlan and perfil.access_vlan not in chaves_habilitadas:
            alvo = titulos_por_chave.get(perfil.access_vlan, perfil.access_vlan)
            raise ValueError(f"{perfil.titulo} aponta acesso para {alvo}, mas essa VLAN nao esta habilitada.")

    return perfis_normalizados


def parse_rede_vlan(valor: str) -> IPv4Network:
    try:
        rede = IPv4Network(valor.strip(), strict=True)
    except ValueError as exc:
        raise ValueError(f"Rede de VLAN invalida: {exc}") from exc

    if rede.prefixlen > 29:
        raise ValueError("Rede de VLAN muito pequena. Use pelo menos /29.")

    return rede


def validar_ip_dns(valor: str, campo: str) -> str:
    try:
        return str(IPv4Address(valor.strip()))
    except ValueError as exc:
        raise ValueError(f"{campo} invalido: {exc}") from exc


def resolver_dns(perfil: str, dns_primario: str = "", dns_secundario: str = "") -> tuple[str, str, str]:
    perfil = normalizar_perfil_dns(perfil)
    if perfil == "custom":
        primario = validar_ip_dns(dns_primario, "DNS primario")
        secundario = validar_ip_dns(dns_secundario, "DNS secundario") if dns_secundario.strip() else ""
        return perfil, primario, secundario

    dados = DNS_PROFILES[perfil]
    return perfil, str(dados["primario"]), str(dados["secundario"])


def criar_configuracao(
    *,
    versao_routeros: int,
    identidade: str,
    usar_pppoe: bool,
    pppoe_usuario: str,
    pppoe_senha: str,
    dns_profile: str,
    dns_primario: str,
    dns_secundario: str,
    rede: str,
    mascara: str,
    criar_dhcp: bool,
    perfil_firewall: str,
    servicos: dict[str, bool],
    interface_wan: str,
    interfaces_lan: str | list[str],
    firewall_opcoes: dict[str, bool] | None = None,
    vlan_perfis: list[dict[str, str | bool | int]] | None = None,
) -> ConfiguracaoAssistente:
    perfil_firewall = normalizar_perfil_firewall(perfil_firewall)
    if versao_routeros not in {6, 7}:
        raise ValueError("Escolha RouterOS v6 ou v7.")
    if perfil_firewall not in PERFIS_FIREWALL:
        raise ValueError("Escolha um perfil de firewall valido.")
    if not identidade.strip():
        raise ValueError("Informe o nome do roteador.")
    if not interface_wan.strip():
        raise ValueError("Informe a interface WAN.")

    lan = normalizar_interfaces_lan(interfaces_lan)
    if interface_wan.strip() in lan:
        raise ValueError("A interface WAN nao pode estar na lista de interfaces LAN.")

    if usar_pppoe:
        if not pppoe_usuario.strip():
            raise ValueError("Informe o usuario PPPoE.")
        if not pppoe_senha:
            raise ValueError("Informe a senha PPPoE.")

    rede_lan = parse_rede_lan(rede, mascara)
    dns_profile, dns_primario, dns_secundario = resolver_dns(dns_profile, dns_primario, dns_secundario)

    return ConfiguracaoAssistente(
        versao_routeros=versao_routeros,
        identidade=identidade.strip(),
        usar_pppoe=usar_pppoe,
        pppoe_usuario=pppoe_usuario.strip(),
        pppoe_senha=pppoe_senha,
        dns_profile=dns_profile,
        dns_primario=dns_primario,
        dns_secundario=dns_secundario,
        rede_lan=rede_lan,
        criar_dhcp=criar_dhcp,
        perfil_firewall=perfil_firewall,
        firewall_opcoes=normalizar_opcoes_firewall(perfil_firewall, versao_routeros, firewall_opcoes),
        servicos={**obter_servicos_padrao(), **servicos},
        interface_wan=interface_wan.strip(),
        interfaces_lan=lan,
        vlan_perfis=normalizar_perfis_vlan(vlan_perfis, rede_lan),
    )


def main() -> None:
    print("\nAssistente rapido de configuracao MikroTik\n")
    print("Este script gera um arquivo .rsc em portugues para RouterOS v6 ou v7.")
    print("Minha sugestao geral: RouterOS v7 + firewall recomendado + Winbox/SSH ligados.\n")

    configuracao = coletar_configuracao()
    script = gerar_script(configuracao)
    destino = salvar_script(configuracao, script)

    print("\nResumo da sugestao aplicada:")
    print(f"- Versao RouterOS: v{configuracao.versao_routeros}")
    print(f"- Perfil de firewall: {PERFIS_FIREWALL[configuracao.perfil_firewall]['titulo']}")
    print(f"- WAN: {configuracao.interface_wan}")
    print(f"- LAN bridge: {configuracao.bridge_name} com {', '.join(configuracao.interfaces_lan)}")
    print(f"- Rede LAN: {configuracao.rede_lan.network_address}/{configuracao.prefixo}")
    if configuracao.vlan_perfis:
        print(f"- VLANs extras: {', '.join(perfil.titulo for perfil in configuracao.vlan_perfis)}")
    print(f"- Arquivo gerado: {destino}")
    print("\nProximo passo: importar ou colar o conteudo do .rsc no MikroTik com cuidado.")


def coletar_configuracao() -> ConfiguracaoAssistente:
    versao = perguntar_versao()
    identidade = perguntar_texto(
        "Nome do roteador (identity)",
        padrao=f"MikroTik-v{versao}",
    )

    interface_wan = perguntar_texto("Interface WAN", padrao="ether1")
    interfaces_lan = perguntar_lista(
        "Interfaces LAN para colocar na bridge",
        padrao="ether2,ether3,ether4,ether5",
    )

    usar_pppoe = perguntar_sim_nao(
        "Deseja configurar PPPoE?",
        padrao=True,
    )
    pppoe_usuario = ""
    pppoe_senha = ""
    if usar_pppoe:
        pppoe_usuario = perguntar_texto("Usuario PPPoE")
        pppoe_senha = perguntar_senha("Senha PPPoE")
        while not pppoe_senha:
            print("A senha PPPoE nao pode ficar vazia.")
            pppoe_senha = perguntar_senha("Senha PPPoE")

    rede_lan = perguntar_rede_lan()
    criar_dhcp = perguntar_sim_nao(
        "Deseja gerar DHCP automaticamente para a LAN?",
        padrao=True,
    )

    perfil_firewall = perguntar_perfil_firewall()
    firewall_opcoes = perguntar_opcoes_firewall(perfil_firewall, versao) if perfil_firewall == "custom" else None
    mostrar_sugestao_servicos()
    servicos = perguntar_servicos()

    return ConfiguracaoAssistente(
        versao_routeros=versao,
        identidade=identidade,
        usar_pppoe=usar_pppoe,
        pppoe_usuario=pppoe_usuario,
        pppoe_senha=pppoe_senha,
        rede_lan=rede_lan,
        criar_dhcp=criar_dhcp,
        perfil_firewall=perfil_firewall,
        firewall_opcoes=normalizar_opcoes_firewall(perfil_firewall, versao, firewall_opcoes),
        servicos=servicos,
        interface_wan=interface_wan,
        interfaces_lan=interfaces_lan,
        vlan_perfis=None,
    )


def perguntar_versao() -> int:
    while True:
        resposta = input("Qual versao do RouterOS voce quer gerar? [6/7] (padrao: 7): ").strip() or "7"
        if resposta in {"6", "7"}:
            return int(resposta)
        print("Digite apenas 6 ou 7.")


def perguntar_rede_lan() -> IPv4Network:
    while True:
        rede = input("Endereco de rede LAN (ex.: 192.168.10.0): ").strip()
        mascara = input("Mascara de sub-rede (ex.: 255.255.255.0 ou /24): ").strip()

        try:
            rede_lan = parse_rede_lan(rede, mascara)
        except ValueError as exc:
            print(exc)
            continue

        return rede_lan


def perguntar_perfil_firewall() -> str:
    print("\nPerfis de firewall disponiveis:")
    for chave in FIREWALL_PROFILE_ORDER:
        dados = PERFIS_FIREWALL[chave]
        print(f"- {chave}: {dados['titulo']} | {dados['descricao']}")
        print(f"  {dados['sugestao']}")

    while True:
        resposta = input("\nEscolha o perfil de firewall [basic/recommended/advanced/custom] (padrao: recommended): ").strip().lower()
        if not resposta:
            return "recommended"
        resposta = normalizar_perfil_firewall(resposta)
        if resposta in PERFIS_FIREWALL:
            return resposta
        print("Opcao invalida. Use basic, recommended, advanced ou custom.")


def perguntar_opcoes_firewall(perfil_firewall: str, versao_routeros: int) -> dict[str, bool]:
    opcoes = obter_opcoes_firewall_padrao("recommended", versao_routeros)
    print("\nModo customizado: escolha quais opcoes de seguranca voce quer usar.")
    for categoria in FIREWALL_CATEGORY_ORDER:
        print(f"\n[{FIREWALL_CATEGORY_TITLES[categoria]}]")
        for nome, dados in FIREWALL_OPTIONS.items():
            if dados["categoria"] != categoria:
                continue
            if nome == "raw_dns_v7" and versao_routeros != 7:
                opcoes[nome] = False
                continue
            print(f"- {dados['titulo']}: {dados['descricao']}")
            opcoes[nome] = perguntar_sim_nao(dados["titulo"], padrao=opcoes[nome])
    return opcoes


def mostrar_sugestao_servicos() -> None:
    print("\nSugestao de servicos:")
    print("- Ligue Winbox.")
    print("- Ligue SSH so se voce realmente usa terminal.")
    print("- Deixe Telnet, FTP, WWW e API desligados na maioria dos cenarios.")
    print("- WWW-SSL e API-SSL so fazem sentido se voce souber que precisa deles.\n")


def perguntar_servicos() -> dict[str, bool]:
    servicos = obter_servicos_padrao()
    for nome, label, padrao, sugestao in SERVICOS_PADRAO:
        print(sugestao)
        servicos[nome] = perguntar_sim_nao(f"Ativar {label}?", padrao=padrao)
    return servicos


def perguntar_texto(pergunta: str, padrao: str | None = None) -> str:
    while True:
        sufixo = f" (padrao: {padrao})" if padrao else ""
        resposta = input(f"{pergunta}{sufixo}: ").strip()
        if resposta:
            return resposta
        if padrao is not None:
            return padrao
        print("Este campo nao pode ficar vazio.")


def perguntar_lista(pergunta: str, padrao: str) -> list[str]:
    while True:
        resposta = input(f"{pergunta} (separadas por virgula) (padrao: {padrao}): ").strip() or padrao
        itens = [item.strip() for item in resposta.split(",") if item.strip()]
        if itens:
            return itens
        print("Informe pelo menos uma interface.")


def perguntar_senha(pergunta: str) -> str:
    if not sys.stdin.isatty():
        return input(f"{pergunta}: ").strip()
    return getpass(f"{pergunta}: ").strip()


def perguntar_sim_nao(pergunta: str, padrao: bool) -> bool:
    marcador = "S/n" if padrao else "s/N"
    while True:
        resposta = input(f"{pergunta} [{marcador}]: ").strip().lower()
        if not resposta:
            return padrao
        if resposta in {"s", "sim", "y", "yes"}:
            return True
        if resposta in {"n", "nao", "no"}:
            return False
        print("Responda com s ou n.")


def gerar_script(config: ConfiguracaoAssistente) -> str:
    blocos = [
        gerar_cabecalho(config),
        gerar_identidade(config),
        gerar_bridge_lan(config),
        gerar_enderecamento_lan(config),
        gerar_dhcp(config),
        gerar_dns(config),
        gerar_pppoe(config),
        gerar_vlans(config),
        gerar_listas_de_interface(config),
        gerar_firewall(config),
        gerar_servicos(config),
    ]
    return "\n\n".join(bloco for bloco in blocos if bloco.strip()).strip() + "\n"


def gerar_cabecalho(config: ConfiguracaoAssistente) -> str:
    return (
        "# Script gerado pelo MikroTik Config Tool\n"
        f"# RouterOS alvo: v{config.versao_routeros}\n"
        f"# Perfil de firewall: {config.perfil_firewall}\n"
        "# Revise antes de aplicar em producao"
    )


def gerar_identidade(config: ConfiguracaoAssistente) -> str:
    return (
        "/system identity\n"
        f'set name="{escape_routeros(config.identidade)}"'
    )


def gerar_bridge_lan(config: ConfiguracaoAssistente) -> str:
    linhas = [
        "/interface bridge",
        f"add name={config.bridge_name} protocol-mode=rstp",
        "",
        "/interface bridge port",
    ]
    for interface in config.interfaces_lan:
        linhas.append(f"add bridge={config.bridge_name} interface={interface}")
    return "\n".join(linhas)


def gerar_enderecamento_lan(config: ConfiguracaoAssistente) -> str:
    return (
        "/ip address\n"
        f"add address={config.ip_lan_router}/{config.prefixo} interface={config.bridge_name} "
        'comment="LAN principal"'
    )


def gerar_dhcp(config: ConfiguracaoAssistente) -> str:
    if not config.criar_dhcp:
        return ""

    return (
        "/ip pool\n"
        f"add name=pool-lan ranges={config.pool_inicio}-{config.pool_fim}\n\n"
        "/ip dhcp-server\n"
        f"add name=dhcp-lan interface={config.bridge_name} address-pool=pool-lan disabled=no\n\n"
        "/ip dhcp-server network\n"
        f"add address={config.rede_lan.network_address}/{config.prefixo} "
        f"gateway={config.ip_lan_router} dns-server={config.ip_lan_router}"
    )


def gerar_dns(config: ConfiguracaoAssistente) -> str:
    servidores = ",".join(config.dns_servers)
    if servidores:
        return f"/ip dns\nset allow-remote-requests=yes servers={servidores}"
    return "/ip dns\nset allow-remote-requests=yes"


def gerar_pppoe(config: ConfiguracaoAssistente) -> str:
    if not config.usar_pppoe:
        return ""

    return (
        "/interface pppoe-client\n"
        f'add name=pppoe-out1 interface={config.interface_wan} user="{escape_routeros(config.pppoe_usuario)}" '
        f'password="{escape_routeros(config.pppoe_senha)}" add-default-route=yes use-peer-dns=no disabled=no'
    )


def gerar_listas_de_interface(config: ConfiguracaoAssistente) -> str:
    linhas = [
        "/interface list",
        'add name=WAN comment="Created by MikroTik Config Tool"',
        'add name=LAN comment="Created by MikroTik Config Tool"',
    ]
    for perfil in config.vlan_perfis:
        linhas.append(f'add name={perfil.list_name} comment="Preset VLAN {perfil.titulo}"')

    linhas.extend(
        [
            "",
            "/interface list member",
            f"add interface={config.interface_internet} list=WAN",
            f"add interface={config.bridge_name} list=LAN",
        ]
    )
    for perfil in config.vlan_perfis:
        interface_name = config.bridge_name if perfil.chave == "main" else perfil.interface_name
        linhas.append(f"add interface={interface_name} list={perfil.list_name}")

    return "\n".join(linhas)


def gerar_vlans(config: ConfiguracaoAssistente) -> str:
    if not config.vlan_perfis:
        return ""

    secoes: list[str] = []

    interface_vlan = ["/interface vlan"]
    bridge_vlan = ["/interface bridge vlan"]
    enderecos = ["/ip address"]
    dhcp_pool = ["/ip pool"]
    dhcp_server = ["/ip dhcp-server"]
    dhcp_network = ["/ip dhcp-server network"]
    queues = ["/queue simple"]
    comentarios = ["# Politicas de VLAN para futura integracao com firewall"]

    for perfil in config.vlan_perfis:
        if perfil.chave != "main":
            interface_vlan.append(
                f"add name={perfil.interface_name} interface={config.bridge_name} vlan-id={perfil.vlan_id} comment=\"Preset {escape_routeros(perfil.titulo)}\""
            )
            bridge_vlan.append(
                f"add bridge={config.bridge_name} vlan-ids={perfil.vlan_id} tagged={config.bridge_name} comment=\"Preset {escape_routeros(perfil.titulo)}\""
            )
            enderecos.append(
                f"add address={perfil.gateway_ip}/{perfil.rede.prefixlen} interface={perfil.interface_name} comment=\"Gateway {escape_routeros(perfil.titulo)}\""
            )

            if perfil.dhcp_proprio:
                dhcp_pool.append(
                    f"add name=pool-{perfil.nome_slug} ranges={perfil.pool_inicio}-{perfil.pool_fim}"
                )
                dhcp_server.append(
                    f"add name=dhcp-{perfil.nome_slug} interface={perfil.interface_name} address-pool=pool-{perfil.nome_slug} disabled=no"
                )
                dns_server = perfil.gateway_ip if perfil.dns_proprio else config.ip_lan_router
                dhcp_network.append(
                    f"add address={perfil.rede.network_address}/{perfil.rede.prefixlen} gateway={perfil.gateway_ip} dns-server={dns_server} comment=\"DHCP {escape_routeros(perfil.titulo)}\""
                )

        if perfil.limite_banda:
            queues.append(
                f"add name=queue-{perfil.nome_slug} target={perfil.rede.network_address}/{perfil.rede.prefixlen} max-limit={perfil.limite_banda} comment=\"Limite {escape_routeros(perfil.titulo)}\""
            )

        comentarios.append(
            f"# {perfil.titulo}: isolada={'sim' if perfil.isolada else 'nao'}, internet_only={'sim' if perfil.internet_only else 'nao'}, access_vlan={perfil.access_vlan or 'nenhuma'}, dhcp_proprio={'sim' if perfil.dhcp_proprio else 'nao'}, dns_proprio={'sim' if perfil.dns_proprio else 'nao'}, limite_banda={perfil.limite_banda or 'sem limite'}"
        )

    for bloco in (interface_vlan, bridge_vlan, enderecos):
        if len(bloco) > 1:
            secoes.append("\n".join(bloco))
    if len(dhcp_pool) > 1:
        secoes.append("\n".join(dhcp_pool))
    if len(dhcp_server) > 1:
        secoes.append("\n".join(dhcp_server))
    if len(dhcp_network) > 1:
        secoes.append("\n".join(dhcp_network))
    if len(queues) > 1:
        secoes.append("\n".join(queues))
    secoes.append("\n".join(comentarios))

    return "\n\n".join(secoes)


def gerar_firewall(config: ConfiguracaoAssistente) -> str:
    opcoes = config.firewall_opcoes
    filtros_input: list[str] = []
    filtros_forward: list[str] = []
    filtros_output: list[str] = []
    nat: list[str] = []
    raw: list[str] = []

    if opcoes["accept_established"]:
        filtros_input.append('add chain=input action=accept connection-state=established,related comment="mtk-tool input established"')
    if opcoes["drop_invalid"]:
        filtros_input.append('add chain=input action=drop connection-state=invalid comment="mtk-tool input invalid"')
    if opcoes["accept_icmp"]:
        filtros_input.append('add chain=input action=accept protocol=icmp comment="mtk-tool input icmp"')
    if opcoes["allow_lan_input"]:
        filtros_input.append('add chain=input action=accept in-interface-list=LAN comment="mtk-tool allow lan management"')
    if opcoes["port_scan"]:
        filtros_input.append('add chain=input action=drop in-interface-list=WAN protocol=tcp psd=21,3s,3,1 comment="mtk-tool drop port scan"')
    if opcoes["ssh_bruteforce"]:
        filtros_input.append('add chain=input action=drop in-interface-list=WAN protocol=tcp dst-port=22 connection-limit=3,32 comment="mtk-tool drop ssh bruteforce"')
    if opcoes["block_dns_wan"]:
        filtros_input.extend(
            [
                'add chain=input action=drop in-interface-list=WAN protocol=udp dst-port=53 comment="mtk-tool drop wan dns udp"',
                'add chain=input action=drop in-interface-list=WAN protocol=tcp dst-port=53 comment="mtk-tool drop wan dns tcp"',
            ]
        )
    if opcoes["log_wan_input"]:
        filtros_input.append('add chain=input action=log in-interface-list=WAN log-prefix="FW-IN " comment="mtk-tool log wan input"')
    if opcoes["drop_wan_input"]:
        filtros_input.append('add chain=input action=drop in-interface-list=WAN comment="mtk-tool drop wan input"')
    if opcoes["forward_established"]:
        filtros_forward.append('add chain=forward action=accept connection-state=established,related comment="mtk-tool forward established"')
    if opcoes["drop_forward_invalid"]:
        filtros_forward.append('add chain=forward action=drop connection-state=invalid comment="mtk-tool forward invalid"')
    if opcoes["log_new_wan_forward"]:
        filtros_forward.append('add chain=forward action=log in-interface-list=WAN connection-state=new log-prefix="FW-FWD " comment="mtk-tool log wan forward"')
    if opcoes["allow_lan_to_wan"]:
        filtros_forward.append('add chain=forward action=accept in-interface-list=LAN out-interface-list=WAN comment="mtk-tool allow lan to wan"')
    if opcoes["allow_dstnat"]:
        filtros_forward.append('add chain=forward action=accept connection-nat-state=dstnat in-interface-list=WAN comment="mtk-tool allow dstnat"')
    if opcoes["drop_new_wan_forward"]:
        filtros_forward.append('add chain=forward action=drop connection-state=new connection-nat-state=!dstnat in-interface-list=WAN comment="mtk-tool drop new wan forward"')
    if opcoes["output_established"]:
        filtros_output.append('add chain=output action=accept connection-state=established,related comment="mtk-tool output established"')
    if opcoes["drop_output_invalid"]:
        filtros_output.append('add chain=output action=drop connection-state=invalid comment="mtk-tool output invalid"')
    if opcoes["nat_masquerade"]:
        nat.append(f'add chain=srcnat action=masquerade out-interface={config.interface_internet} comment="mtk-tool nat masquerade"')
    if opcoes["raw_dns_v7"] and config.versao_routeros == 7:
        raw.extend(
            [
                'add chain=prerouting action=drop in-interface-list=WAN protocol=udp dst-port=53 comment="mtk-tool raw dns udp"',
                'add chain=prerouting action=drop in-interface-list=WAN protocol=tcp dst-port=53 comment="mtk-tool raw dns tcp"',
            ]
        )

    secoes: list[str] = []
    filtros: list[str] = []
    if filtros_input:
        filtros.extend(["# input", *filtros_input])
    if filtros_forward:
        if filtros:
            filtros.append("")
        filtros.extend(["# forward", *filtros_forward])
    if filtros_output:
        if filtros:
            filtros.append("")
        filtros.extend(["# output", *filtros_output])

    if filtros:
        secoes.append("/ip firewall filter\n" + "\n".join(filtros))
    if nat:
        secoes.append("/ip firewall nat\n" + "\n".join(nat))
    if raw:
        secoes.append("/ip firewall raw\n" + "\n".join(raw))
    return "\n\n".join(secoes)


def gerar_servicos(config: ConfiguracaoAssistente) -> str:
    linhas = ["/ip service"]
    for nome, _, _, _ in SERVICOS_PADRAO:
        disabled = "no" if config.servicos.get(nome, False) else "yes"
        linhas.append(f"set [find name={nome}] disabled={disabled}")
    return "\n".join(linhas)


def salvar_script(config: ConfiguracaoAssistente, script: str) -> Path:
    nome_padrao = f"config_mikrotik_v{config.versao_routeros}.rsc"
    nome_arquivo = perguntar_texto(
        "Nome do arquivo de saida",
        padrao=nome_padrao,
    )
    destino = Path(nome_arquivo).expanduser()
    if not destino.is_absolute():
        destino = Path.cwd() / destino
    destino.write_text(script, encoding="utf-8")
    return destino


def escape_routeros(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace('"', '\\"')


if __name__ == "__main__":
    main()
