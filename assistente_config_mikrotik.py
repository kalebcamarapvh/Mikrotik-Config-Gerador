from __future__ import annotations

from dataclasses import dataclass
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

PERFIS_FIREWALL = {
    "basic": {
        "titulo": "Basico",
        "descricao": "Boa base para casa e escritorio pequeno.",
        "sugestao": "Sugestao: use BASICO se voce quer algo simples e seguro sem exagero.",
        "quando_usar": "Instalacao simples e mais compativel.",
    },
    "medium": {
        "titulo": "Medio",
        "descricao": "Adiciona protecoes extras de porta e exposicao WAN.",
        "sugestao": "Sugestao: use MEDIO na maioria dos casos. E o melhor equilibrio.",
        "quando_usar": "Melhor equilibrio para a maioria dos cenarios.",
    },
    "advanced": {
        "titulo": "Avancado",
        "descricao": "Mais log, mais bloqueios e regra raw no RouterOS v7.",
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
    },
    "drop_invalid": {
        "titulo": "Descartar conexoes invalidas",
        "descricao": "Remove pacotes quebrados ou fora de estado para limpar ruido.",
    },
    "accept_icmp": {
        "titulo": "Permitir ICMP (ping)",
        "descricao": "Facilita testes de rede e diagnostico basico.",
    },
    "allow_lan_input": {
        "titulo": "Permitir acesso ao roteador pela LAN",
        "descricao": "Autoriza gerenciamento do MikroTik a partir da rede local.",
    },
    "drop_wan_input": {
        "titulo": "Bloquear acesso ao roteador pela WAN",
        "descricao": "Impede tentativas diretas da internet contra o proprio roteador.",
    },
    "forward_established": {
        "titulo": "Permitir forward estabelecido",
        "descricao": "Mantem o trafego ja em andamento entre LAN e internet.",
    },
    "drop_forward_invalid": {
        "titulo": "Descartar forward invalido",
        "descricao": "Elimina pacotes de encaminhamento inconsistentes.",
    },
    "allow_lan_to_wan": {
        "titulo": "Permitir LAN para internet",
        "descricao": "Libera a saida da rede local para a WAN.",
    },
    "allow_dstnat": {
        "titulo": "Permitir trafego encaminhado (dstnat)",
        "descricao": "Mantem redirecionamentos de porta funcionando quando existirem.",
    },
    "drop_new_wan_forward": {
        "titulo": "Bloquear novas conexoes vindas da WAN",
        "descricao": "Evita que trafego novo da internet entre na LAN sem regra explicita.",
    },
    "nat_masquerade": {
        "titulo": "Aplicar NAT masquerade",
        "descricao": "Permite que a rede local navegue usando o IP da WAN.",
    },
    "port_scan": {
        "titulo": "Bloquear port scan",
        "descricao": "Detecta sondagens simples de portas na interface WAN.",
    },
    "ssh_bruteforce": {
        "titulo": "Proteger SSH contra brute force",
        "descricao": "Bloqueia tentativas repetidas no servico SSH.",
    },
    "block_dns_wan": {
        "titulo": "Bloquear DNS vindo da WAN",
        "descricao": "Evita uso indevido do roteador como resolvedor exposto.",
    },
    "log_wan_input": {
        "titulo": "Registrar tentativas na WAN",
        "descricao": "Gera logs de acesso ao roteador vindo da internet.",
    },
    "log_new_wan_forward": {
        "titulo": "Registrar novas conexoes WAN para frente",
        "descricao": "Ajuda a auditar tentativas novas de trafego vindo da WAN.",
    },
    "raw_dns_v7": {
        "titulo": "Bloqueio raw de DNS na WAN (v7)",
        "descricao": "Usa raw table no RouterOS v7 para derrubar DNS indesejado cedo.",
    },
}


@dataclass
class ConfiguracaoAssistente:
    versao_routeros: int
    identidade: str
    usar_pppoe: bool
    pppoe_usuario: str
    pppoe_senha: str
    rede_lan: IPv4Network
    criar_dhcp: bool
    perfil_firewall: str
    firewall_opcoes: dict[str, bool]
    servicos: dict[str, bool]
    interface_wan: str
    interfaces_lan: list[str]

    @property
    def bridge_name(self) -> str:
        return "bridge-lan"

    @property
    def interface_internet(self) -> str:
        if self.usar_pppoe:
            return "pppoe-out1"
        return self.interface_wan

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


def obter_servicos_padrao() -> dict[str, bool]:
    return {nome: padrao for nome, _, padrao, _ in SERVICOS_PADRAO}


def obter_opcoes_firewall_padrao(perfil: str, versao_routeros: int) -> dict[str, bool]:
    if perfil not in PERFIS_FIREWALL:
        raise ValueError("Escolha um perfil de firewall valido.")

    opcoes = {nome: False for nome in FIREWALL_OPTIONS}

    base = {
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
    }
    medio = {"port_scan", "ssh_bruteforce", "block_dns_wan"}
    avancado = {"log_wan_input", "log_new_wan_forward"}

    ativos = set(base)
    if perfil in {"medium", "advanced", "custom"}:
        ativos.update(medio)
    if perfil == "advanced":
        ativos.update(avancado)
        if versao_routeros == 7:
            ativos.add("raw_dns_v7")

    for nome in ativos:
        opcoes[nome] = True

    return opcoes


def normalizar_opcoes_firewall(
    perfil_firewall: str,
    versao_routeros: int,
    firewall_opcoes: dict[str, bool] | None = None,
) -> dict[str, bool]:
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


def criar_configuracao(
    *,
    versao_routeros: int,
    identidade: str,
    usar_pppoe: bool,
    pppoe_usuario: str,
    pppoe_senha: str,
    rede: str,
    mascara: str,
    criar_dhcp: bool,
    perfil_firewall: str,
    servicos: dict[str, bool],
    interface_wan: str,
    interfaces_lan: str | list[str],
    firewall_opcoes: dict[str, bool] | None = None,
) -> ConfiguracaoAssistente:
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

    return ConfiguracaoAssistente(
        versao_routeros=versao_routeros,
        identidade=identidade.strip(),
        usar_pppoe=usar_pppoe,
        pppoe_usuario=pppoe_usuario.strip(),
        pppoe_senha=pppoe_senha,
        rede_lan=parse_rede_lan(rede, mascara),
        criar_dhcp=criar_dhcp,
        perfil_firewall=perfil_firewall,
        firewall_opcoes=normalizar_opcoes_firewall(perfil_firewall, versao_routeros, firewall_opcoes),
        servicos={**obter_servicos_padrao(), **servicos},
        interface_wan=interface_wan.strip(),
        interfaces_lan=lan,
    )


def main() -> None:
    print("\nAssistente rapido de configuracao MikroTik\n")
    print("Este script gera um arquivo .rsc em portugues para RouterOS v6 ou v7.")
    print("Minha sugestao geral: RouterOS v7 + firewall medio + Winbox/SSH ligados.\n")

    configuracao = coletar_configuracao()
    script = gerar_script(configuracao)
    destino = salvar_script(configuracao, script)

    print("\nResumo da sugestao aplicada:")
    print(f"- Versao RouterOS: v{configuracao.versao_routeros}")
    print(f"- Perfil de firewall: {PERFIS_FIREWALL[configuracao.perfil_firewall]['titulo']}")
    print(f"- WAN: {configuracao.interface_wan}")
    print(f"- LAN bridge: {configuracao.bridge_name} com {', '.join(configuracao.interfaces_lan)}")
    print(f"- Rede LAN: {configuracao.rede_lan.network_address}/{configuracao.prefixo}")
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
    for chave, dados in PERFIS_FIREWALL.items():
        print(f"- {chave}: {dados['titulo']} | {dados['descricao']}")
        print(f"  {dados['sugestao']}")

    while True:
        resposta = input("\nEscolha o perfil de firewall [basic/medium/advanced/custom] (padrao: medium): ").strip().lower()
        if not resposta:
            return "medium"
        if resposta in PERFIS_FIREWALL:
            return resposta
        print("Opcao invalida. Use basic, medium, advanced ou custom.")


def perguntar_opcoes_firewall(perfil_firewall: str, versao_routeros: int) -> dict[str, bool]:
    opcoes = obter_opcoes_firewall_padrao("medium", versao_routeros)
    print("\nModo customizado: escolha quais opcoes de seguranca voce quer usar.")
    for nome, dados in FIREWALL_OPTIONS.items():
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
    if config.usar_pppoe:
        return "/ip dns\nset allow-remote-requests=yes"
    return "/ip dns\nset allow-remote-requests=yes servers=1.1.1.1,8.8.8.8"


def gerar_pppoe(config: ConfiguracaoAssistente) -> str:
    if not config.usar_pppoe:
        return ""

    return (
        "/interface pppoe-client\n"
        f'add name=pppoe-out1 interface={config.interface_wan} user="{escape_routeros(config.pppoe_usuario)}" '
        f'password="{escape_routeros(config.pppoe_senha)}" add-default-route=yes use-peer-dns=yes disabled=no'
    )


def gerar_listas_de_interface(config: ConfiguracaoAssistente) -> str:
    return (
        "/interface list\n"
        'add name=WAN comment="Created by MikroTik Config Tool"\n'
        'add name=LAN comment="Created by MikroTik Config Tool"\n\n'
        "/interface list member\n"
        f"add interface={config.interface_internet} list=WAN\n"
        f"add interface={config.bridge_name} list=LAN"
    )


def gerar_firewall(config: ConfiguracaoAssistente) -> str:
    opcoes = config.firewall_opcoes
    filtros: list[str] = []
    nat: list[str] = []
    raw: list[str] = []

    if opcoes["accept_established"]:
        filtros.append('add chain=input action=accept connection-state=established,related,untracked comment="mtk-tool input established"')
    if opcoes["drop_invalid"]:
        filtros.append('add chain=input action=drop connection-state=invalid comment="mtk-tool input invalid"')
    if opcoes["accept_icmp"]:
        filtros.append('add chain=input action=accept protocol=icmp comment="mtk-tool input icmp"')
    if opcoes["allow_lan_input"]:
        filtros.append('add chain=input action=accept in-interface-list=LAN comment="mtk-tool allow lan management"')
    if opcoes["port_scan"]:
        filtros.append('add chain=input action=drop in-interface-list=WAN protocol=tcp psd=21,3s,3,1 comment="mtk-tool drop port scan"')
    if opcoes["ssh_bruteforce"]:
        filtros.append('add chain=input action=drop in-interface-list=WAN protocol=tcp dst-port=22 connection-limit=3,32 comment="mtk-tool drop ssh bruteforce"')
    if opcoes["block_dns_wan"]:
        filtros.extend(
            [
                'add chain=input action=drop in-interface-list=WAN protocol=udp dst-port=53 comment="mtk-tool drop wan dns udp"',
                'add chain=input action=drop in-interface-list=WAN protocol=tcp dst-port=53 comment="mtk-tool drop wan dns tcp"',
            ]
        )
    if opcoes["log_wan_input"]:
        filtros.append('add chain=input action=log in-interface-list=WAN log-prefix="FW-IN " comment="mtk-tool log wan input"')
    if opcoes["drop_wan_input"]:
        filtros.append('add chain=input action=drop in-interface-list=WAN comment="mtk-tool drop wan input"')
    if opcoes["forward_established"]:
        filtros.append('add chain=forward action=accept connection-state=established,related,untracked comment="mtk-tool forward established"')
    if opcoes["drop_forward_invalid"]:
        filtros.append('add chain=forward action=drop connection-state=invalid comment="mtk-tool forward invalid"')
    if opcoes["log_new_wan_forward"]:
        filtros.append('add chain=forward action=log in-interface-list=WAN connection-state=new log-prefix="FW-FWD " comment="mtk-tool log wan forward"')
    if opcoes["allow_lan_to_wan"]:
        filtros.append('add chain=forward action=accept in-interface-list=LAN out-interface-list=WAN comment="mtk-tool allow lan to wan"')
    if opcoes["allow_dstnat"]:
        filtros.append('add chain=forward action=accept connection-nat-state=dstnat in-interface-list=WAN comment="mtk-tool allow dstnat"')
    if opcoes["drop_new_wan_forward"]:
        filtros.append('add chain=forward action=drop connection-state=new connection-nat-state=!dstnat in-interface-list=WAN comment="mtk-tool drop new wan forward"')
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
