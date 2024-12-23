#!/bin/sh -e


export MEDIA_ROOT="${MEDIA_ROOT:-/var/run/app/media}"
export STATIC_ROOT="${STATIC_ROOT:-/var/run/app/static}"
export UWSGI_PROCESSES="${UWSGI_PROCESSES:-"4"}"
export DJANGO_SETTINGS_MODULE="hope_payment_gateway.config.settings"

case "$1" in
    run)
      django-admin upgrade --with-check
	    set -- tini -- "$@"
	    MAPPING=""
	    if [ "${STATIC_URL}" = "/static/" ]; then
	      MAPPING="--static-map ${STATIC_URL}=${STATIC_ROOT}"
	    fi
      set -- tini -- "$@"
	    set -- uwsgi --http :8000 \
	          -H /venv \
	          --module hope_payment_gateway.config.wsgi \
	          --mimefile=/conf/mime.types \
	          --uid hope \
	          --gid unicef \
            --buffer-size 8192 \
            --http-buffer-size 8192 \
	          $MAPPING
	    ;;
    upgrade)
      django-admin upgrade --with-check
      ;;
    worker)
      set -- tini -- "$@"
      set -- gosu hope:unicef celery -A hope_payment_gateway.config.celery worker --concurrency=4 -E --loglevel=ERROR
      ;;
    beat)
      set -- tini -- "$@"
      set -- gosu hope:unicef celery -A hope_payment_gateway.config.celery beat --loglevel=ERROR --scheduler django_celery_beat.schedulers:DatabaseScheduler
      ;;
    flower)
      export DATABASE_URL="sqlite://:memory:"
      set -- tini -- "$@"
      set -- gosu hope:unicef celery -A hope_payment_gateway.config.celery flower
      ;;
esac

exec "$@"
