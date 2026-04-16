from __future__ import annotations

import sys


def _format_import_error(exc: ImportError) -> str:
    message = str(exc)

    if "_tkinter" in message or "libtk" in message or "tkinter" in message:
        return (
            "Failed to start the MikroTik Config Tool because the Tk GUI runtime is missing.\n"
            "This app needs Tkinter plus the system Tk libraries.\n"
            "On Linux, install the Tk runtime for your distribution and try again.\n"
            f"Import error: {exc}"
        )

    return (
        "Failed to start the MikroTik Config Tool.\n"
        "Install dependencies with `pip install -r requirements.txt`.\n"
        f"Import error: {exc}"
    )


def main() -> int:
    try:
        import tkinter  # noqa: F401
        from gui.app import launch
    except ImportError as exc:
        print(_format_import_error(exc), file=sys.stderr)
        return 1

    launch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
