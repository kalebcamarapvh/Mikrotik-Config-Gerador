from __future__ import annotations

from typing import Any

from .models import RouterInfo

try:
    from librouteros import connect as routeros_connect
except ImportError:  # pragma: no cover - depends on installed extras
    routeros_connect = None


class RouterConnection:
    def __init__(self) -> None:
        self.api: Any | None = None
        self.last_error: str | None = None

    def connect(self, host: str, user: str, password: str, port: int = 8728) -> bool:
        self.disconnect()

        if routeros_connect is None:
            self.last_error = "librouteros is not installed."
            return False

        try:
            self.api = routeros_connect(
                host=host,
                username=user,
                password=password,
                port=port,
            )
        except Exception as exc:  # pragma: no cover - network dependent
            self.api = None
            self.last_error = self._format_exception(exc)
            return False

        self.last_error = None
        return True

    def disconnect(self) -> None:
        if self.api is None:
            return

        close = getattr(self.api, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
        self.api = None

    def is_connected(self) -> bool:
        return self.api is not None

    def run_command(self, cmd: str, **params: Any) -> list[dict[str, Any]]:
        if self.api is None:
            raise RuntimeError("Router is not connected.")

        try:
            result = self.api(cmd=cmd, **params)
            if result is None:
                return []
            return [dict(item) for item in result]
        except Exception as exc:  # pragma: no cover - network dependent
            raise RuntimeError(self._format_exception(exc)) from exc

    def get_resource(self) -> dict[str, Any]:
        rows = self.run_command("/system/resource/print")
        return rows[0] if rows else {}

    def get_identity(self) -> str:
        rows = self.run_command("/system/identity/print")
        if not rows:
            return ""
        return str(rows[0].get("name", ""))

    def detect_version(self) -> RouterInfo:
        resource = self.get_resource()
        version = str(resource.get("version", ""))
        version_number = version.split(" ", 1)[0]
        major_text = version_number.split(".", 1)[0] if version_number else "7"

        try:
            major = int(major_text)
        except ValueError:
            major = 7

        memory_bytes = resource.get("total-memory") or resource.get("free-memory") or 0
        try:
            ram_mb = int(int(memory_bytes) / (1024 * 1024))
        except (TypeError, ValueError):
            ram_mb = 0

        return RouterInfo(
            major=major,
            full=version_number,
            board=str(resource.get("board-name", "")),
            ram_mb=ram_mb,
            cpu=str(resource.get("cpu", resource.get("cpu-name", ""))),
            identity=self.get_identity(),
        )

    @staticmethod
    def _format_exception(exc: Exception) -> str:
        message = str(exc).strip()
        return message or exc.__class__.__name__
