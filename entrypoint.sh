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
    prd)
        export PYTHONPATH=/code/src # hack to find django settings
        uwsgi \
            --http :8000 \
            --master \
            --module=src.hope_payment_gateway.config.wsgi \
            --processes=2
    ;;
    *)
        exec "$@"
    ;;
esac