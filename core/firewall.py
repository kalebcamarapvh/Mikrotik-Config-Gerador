from __future__ import annotations

from .models import FirewallConfig, FirewallRules


RULE_METADATA = {
    "accept_established": "Accept established/related",
    "drop_invalid": "Drop invalid",
    "accept_icmp": "Accept ICMP",
    "accept_lan_input": "Accept input from LAN bridge",
    "masquerade": "NAT masquerade on WAN",
    "port_scan_detection": "Port scan detection",
    "ssh_bruteforce": "SSH brute-force protection",
    "bogon_drop": "Drop bogon/RFC1918 on WAN",
    "rate_limit_new": "Rate-limit new connections",
    "tarpit_offenders": "Tarpit repeated offenders",
    "dns_amplification": "DNS amplification protection",
    "explicit_forward": "Explicit forward chain rules",
    "log_drops": "Log dropped packets",
    "raw_table": "Raw table hardening (v7 only)",
}

PRESET_DETAILS = {
    "basic": [
        "Accept established, related connections",
        "Drop invalid connections",
        "Accept ICMP",
        "Drop all other WAN input",
        "Masquerade LAN traffic on WAN",
    ],
    "medium": [
        "Everything in Basic",
        "Port scan detection and drop",
        "SSH brute-force protection",
        "Bogon filtering on WAN input",
        "Rate limiting for new connections",
    ],
    "advanced": [
        "Everything in Medium",
        "Tarpit repeated offenders",
        "DNS amplification protection",
        "Explicit forward chain rules",
        "Raw table rules for RouterOS v7",
        "Logging on drop actions",
    ],
}


def build_firewall_rules(preset: str) -> FirewallRules:
    rules = FirewallRules()

    if preset in {"medium", "advanced"}:
        rules.port_scan_detection = True
        rules.ssh_bruteforce = True
        rules.bogon_drop = True
        rules.rate_limit_new = True

    if preset == "advanced":
        rules.tarpit_offenders = True
        rules.dns_amplification = True
        rules.explicit_forward = True
        rules.log_drops = True
        rules.raw_table = True

    return rules


def build_firewall_config(preset: str) -> FirewallConfig:
    return FirewallConfig(preset=preset, rules=build_firewall_rules(preset))
