#!/bin/bash

set -eou pipefail

case "$1" in
    dev)
        python3 manage.py runserver 0.0.0.0:8000 
    ;;
    *)
        exec "$@"
    ;;
esac
