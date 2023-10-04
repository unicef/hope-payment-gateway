#!/bin/bash

set -eou pipefail

export PYTHONPATH=/code/src # without this, uwsgi can't load python modules

production() {
    python3 manage.py upgrade --all
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
        python3 manage.py upgrade --all
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