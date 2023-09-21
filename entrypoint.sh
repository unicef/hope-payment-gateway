#!/bin/bash

set -eou pipefail

case "$1" in
    dev)
        python3 manage.py migrate
        python3 manage.py runserver 0.0.0.0:8000 
    ;;
    tests)
        python3 manage.py migrate
        pytest
    ;;
    *)
        exec "$@"
    ;;
esac