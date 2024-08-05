#!/bin/bash

set -eou pipefail

production() {
    uwsgi \
        --http :8000 \
        --master \
        --module=hope_payment_gateway.config.wsgi \
        --processes=2 \
        --buffer-size=8192
}

if [ $# -eq 0 ]; then
    production
fi

case "$1" in
    dev)
        ./docker/wait-for-it.sh db:5432
        python3 manage.py upgrade
        python3 manage.py runserver 0.0.0.0:8000
    ;;
    tests)
        ./docker/wait-for-it.sh db:5432
        pytest --create-db
    ;;
    prd)
        production
    ;;
    celery_worker)
        export C_FORCE_ROOT=1
        celery -A hope_payment_gateway.celery worker -l info
    ;;
    celery_beat)
        celery -A hope_payment_gateway.celery beat -l info
    ;;
    celery_flower)
        celery flower -A hope_payment_gateway.celery --port=5555
    ;;
    *)
        exec "$@"
    ;;
esac