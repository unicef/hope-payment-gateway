#!/bin/bash -e
mkdir -p /var/hope_payment_gateway/static
mkdir -p /var/hope_payment_gateway/log
mkdir -p /var/hope_payment_gateway/conf
mkdir -p /var/hope_payment_gateway/run

# chown hope_payment_gateway:hope_payment_gateway -R /var/hope_payment_gateway/


if [[ "$*" == "worker" ]];then
    celery -A hope_payment_gateway.config \
            worker \
            --events \
            --max-tasks-per-child=1 \
            --loglevel=${CELERY_LOGLEVEL} \
            --autoscale=${CELERY_AUTOSCALE} \
            --pidfile run/celery.pid \
            $CELERY_EXTRA


elif [[ "$*" == "beat" ]];then
    celery -A hope_payment_gateway.config beat \
            $CELERY_EXTRA \
            --loglevel=${CELERY_LOGLEVEL} \
            --pidfile run/celerybeat.pid

elif [[ "$*" == "w2" ]];then
    django-admin db_isready --wait --timeout 60

elif [[ "$*" == "hope_payment_gateway" ]];then
    rm -f /var/hope_payment_gateway/run/*

    django-admin diffsettings --output unified
#    django-admin makemigrations --check --dry-run

#    django-admin db_isready --wait --timeout 60
    django-admin check --deploy
    django-admin remove_stale_contenttypes --noinput
    django-admin init_setup --all --verbosity 2
#    django-admin db_isready --wait --timeout 300
    echo "uwsgi --static-map ${STATIC_URL}=${STATIC_ROOT}"
#    exec gosu hope_payment_gateway uwsgi --static-map ${STATIC_URL}=${STATIC_ROOT}
#    newrelic-admin run-program
    uwsgi --static-map ${STATIC_URL}=${STATIC_ROOT}
else
    exec "$@"
fi
