#!/usr/bin/env python
"""Django command-line utility for administrative tasks."""
import os, sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synapse_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django. Activate your virtual environment.") from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
