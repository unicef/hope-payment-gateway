#!/bin/bash

set -eou pipefail

export PYTHONPATH="$PYTHONPATH:/code/src" # without this, uwsgi can't load python modules

production() {
    uwsgi \
        --http :8000 \
        --master \
        --module=src.hope_payment_gateway.config.wsgi \
        --processes=2 \
        --buffer-size=8192
}

if [ $# -eq 0 ]; then
    production
fi

case "$1" in
    dev)
        python3 manage.py upgrade
        python3 manage.py runserver 0.0.0.0:8000 
    ;;
    tests)
        python3 manage.py migrate
        pytest
    ;;
    prd)
        production
    ;;
    celery_worker)
        export C_FORCE_ROOT=1
        celery -A src.hope_payment_gateway.celery worker -l info
    ;;
    *)
        exec "$@"
    ;;
esac