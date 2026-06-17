FROM python:3.14-slim-bookworm AS base_os
ARG GOSU_VERSION=1.19
ARG GOSU_SHA256=52c8749d0142edd234e9d6bd5237dff2d81e71f43537e2f4f66f75dd4b243dd0
ARG VERSION
ARG GIT_SHA
ARG BUILD_DATE

RUN set -x \
  && runtimeDeps=" \
    gettext \
    libmagic1 \
    libxml2 \
    libldap-2.5-0 \
  " \
  && buildDeps=" \
wget \
" \
  && apt-get update && apt-get install -y --no-install-recommends ${buildDeps} ${runtimeDeps} \
  && wget --quiet -O /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-amd64" \
  && echo "$GOSU_SHA256 /usr/local/bin/gosu" | sha256sum --check --status \
  && chmod +x /usr/local/bin/gosu \
  && apt-get purge -y --auto-remove $buildDeps

RUN groupadd --gid 1024 unicef \
    && adduser --disabled-login --disabled-password --no-create-home --ingroup unicef -q hope

# ------- deps -------
FROM base_os AS deps
RUN set -x \
    && buildDeps="build-essential \
cmake \
curl \
gcc \
git \
libfontconfig1 \
libgconf-2-4 \
libglib2.0-0 \
libldap2-dev \
libnss3 \
libsasl2-dev \
libssl-dev \
libxml2-dev  \
libzbar-dev \
python3-dev \
zlib1g-dev  \
" \
    && apt-get update \
    && apt-get install -y --no-install-recommends $buildDeps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uwsgi uv

# ------- builder -------
FROM deps AS builder
ENV VIRTUAL_ENV=/venv \
    UV_PROJECT_ENVIRONMENT=/venv \
    HATCH_VCS_VERSION=${VERSION} \
    SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

RUN <<EOF cat> /RELEASE
{"version": "$VERSION",
  "commit_sha": "$GIT_SHA",
  "date": "$BUILD_DATE"
}
EOF
WORKDIR /code
COPY . /code

RUN uv venv $VIRTUAL_ENV \
    && uv sync --frozen --no-editable

FROM base_os AS dist
ADD docker/conf /conf/
ADD docker/bin/* /usr/local/bin/

COPY --from=builder /usr/local/bin/uwsgi /usr/local/bin/
COPY --from=builder /venv /venv

ENV PATH=/venv/bin:/usr/local/bin/:/usr/bin:/bin:/usr/sbin \
    VERSION=$VERSION \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE="hope_payment_gateway.config.settings" \
    STATIC_URL="/static/" \
    PYTHONPATH="" \
    GIT_SHA=$GIT_SHA \
    BUILD_DATE=$BUILD_DATE \
    PGSSLCERT="/tmp/postgresql.crt" \
    UWSGI_PROCESSES=4

EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["run"]


LABEL org.opencontainers.image.authors="hope@unicef.org"
LABEL org.opencontainers.image.created="$BUILD_DATE"
LABEL org.opencontainers.image.description="Hope Payment Gateway"
LABEL org.opencontainers.image.licenses="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/blob/${SOURCE_COMMIT:-master}/LICENSE"
LABEL org.opencontainers.image.revision=$GIT_SHA
LABEL org.opencontainers.image.source="https://github.com/unicef/hope-payment-gateway/tree/${GIT_SHA:-develop}/"
LABEL org.opencontainers.image.title="Hope Payment Gateway"
LABEL org.opencontainers.image.version="$VERSION"
LABEL org.opencontainers.image.vendor="UNICEF"
