#!/bin/sh -e


export MEDIA_ROOT="${MEDIA_ROOT:-/var/run/app/media}"
export STATIC_ROOT="${STATIC_ROOT:-/var/run/app/static}"
export UWSGI_PROCESSES="${UWSGI_PROCESSES:-"4"}"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-"hope_payment_gateway.config.settings"}"

case "$1" in
    run)
      django-admin upgrade --with-check
	    set -- tini -- "$@"
	    MAPPING=""
	    if [ "${STATIC_URL}" = "/static/" ]; then
	      MAPPING="--static-map ${STATIC_URL}=${STATIC_ROOT}"
	    fi
	    uwsgi --http :8000 \
	          --module hope_payment_gateway.config.wsgi \
	          --uid user \
	          --gid app \
	          $MAPPING
	    ;;
    worker)
      exec celery -A hope_payment_gateway.celery worker -E --loglevel=ERROR --concurrency=4
      ;;
    beat)
      exec celery -A hope_payment_gateway.celery beat -E --loglevel=ERROR ---scheduler django_celery_beat.schedulers:DatabaseScheduler
      ;;
esac

exec "$@"
