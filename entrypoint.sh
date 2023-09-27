#!/bin/bash

set -eou pipefail

production() {
    # export PYTHONPATH=/code/src # hack to find django settings
    uwsgi \
        --http :8000 \
        --master \
        --module=src.hope_payment_gateway.config.wsgi \
        --processes=2
}

if [ $# -eq 0 ]; then
    production
fi

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
        production
    ;;
    *)
        exec "$@"
    ;;
esac