#!/usr/bin/env python
import os
import sys

SRC = os.path.abspath("src")
sys.path.insert(0, SRC)
if sys.argv[1] == "test":
    os.chdir(os.path.join(SRC, "hope_payment_gateway"))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hope_payment_gateway.config.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
