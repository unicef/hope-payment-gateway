#!/bin/bash

set -eou pipefail

case "$1" in
    dev)
        python3 manage.py migrate
        python3 manage.py runserver 0.0.0.0:8000 
    ;;
    worker)
        # https://docs.celeryq.dev/en/stable/userguide/daemonizing.html#running-the-worker-with-superuser-privileges-root
        C_FORCE_ROOT=true \
            celery -A hope_payment_gateway.config worker --events --max-tasks-per-child=1 --loglevel=INFO --autoscale=10,1
    ;;
    tests)
        python3 manage.py migrate
        pytest
    ;;
    *)
        exec "$@"
    ;;
esac
