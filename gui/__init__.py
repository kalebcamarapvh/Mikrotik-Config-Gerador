from .app import MikrotikGeneratorApp, launch

# Backward-compatible alias for older imports.
MikrotikApp = MikrotikGeneratorApp

__all__ = ["MikrotikGeneratorApp", "MikrotikApp", "launch"]
