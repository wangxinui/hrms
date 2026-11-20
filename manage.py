#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # runserver 未指定地址时，默认使用 8001 端口（8000 已被其他项目占用）
    if len(sys.argv) > 1 and sys.argv[1] == "runserver" and len(sys.argv) == 2:
        sys.argv.append("8001")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hrms.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
