FROM python:3.12-slim-bookworm as base

RUN apt update \
    && apt install --no-install-recommends -y \
        gcc curl libgdal-dev \
    && apt clean && rm -rf /var/lib/apt/lists/* \
    && addgroup --system --gid 82 hpg \
    && adduser \
        --system --uid 82 \
        --disabled-password --home /home/hpg \
        --shell /sbin.nologin --group hpg --gecos hpg \
    && mkdir -p /app /tmp /data /static \
    && chown -R hpg:hpg /app /tmp /data /static

ENV PATH=/app/.venv/bin:/usr/local/bin/:/usr/bin:/bin \
    DJANGO_SETTINGS_MODULE=hope_payment_gateway.config.settings \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=""\
    UWSGI_PROCESSES=4

WORKDIR /app
COPY uv.lock README.md MANIFEST.in pyproject.toml /app/
COPY src /app/src/


FROM base as builder

WORKDIR /app
RUN pip install uv
COPY ../uv.lock ../README.md ../MANIFEST.in ../pyproject.toml ./

RUN --mount=type=cache,target=/root/.uv-cache \
    uv sync --cache-dir=/root/.uv-cache \
        --python=/usr/local/bin/python \
        --python-preference=system \
        --frozen

FROM builder AS dev

RUN --mount=type=cache,target=/root/.uv-cache \
    uv sync --cache-dir=/root/.uv-cache \
        --python=/usr/local/bin/python \
        --python-preference=system \
        --frozen
RUN uv pip install . uwsgi

WORKDIR /app
COPY .. ./

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]


FROM base AS prd

ARG BUILD_DATE
ARG VERSION
ARG GIT_SHA
ARG BRANCH

ENV PATH=$PATH:/app/.venv/bin/ \
    BUILD_DATE=$BUILD_DATE \
    GIT_SHA=$GIT_SHA \
    VERSION=$VERSION \
    BRANCH=$BRANCH \
    DJANGO_SETTINGS_MODULE=hope_payment_gateway.config.settings

RUN pip install uv uwsgi

RUN --mount=type=cache,target=/root/.uv-cache \
    --mount=type=bind,source=./src/hope_payment_gateway,target=/app/src/hope_payment_gateway \
    --mount=type=bind,source=./src/hope_api_auth,target=/app/src/hope_api_auth \
    uv sync --cache-dir=/root/.uv-cache \
        --python=/usr/local/bin/python \
        --python-preference=system \
        --frozen \
    uv pip install .

COPY --chown=hpg:hpg .. ./
COPY --chown=hpg:hpg --from=builder /app /app
USER hpg

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]

LABEL maintainer="hope@unicef.org"
LABEL org.opencontainers.image.authors="hope@unicef.org"
LABEL org.opencontainers.image.description="Hope Payment Gateway"
LABEL org.opencontainers.image.documentation="https://github.com/unicef/hope-payment-gateway/"
LABEL org.opencontainers.image.title="Hope Payment Gateway"
LABEL org.opencontainers.image.licenses="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/blob/${GIT_SHA:-master}/LICENSE"
LABEL org.opencontainers.image.revision=$GIT_SHA
LABEL org.opencontainers.image.source="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/tree/${GIT_SHA:-master}/"
LABEL org.opencontainers.image.url="https://hub.docker.com/repository/docker/unicef/hope-payment-gateway/tags/"
LABEL org.opencontainers.image.vendor="UNICEF"
LABEL org.opencontainers.image.created="$BUILD_DATE"
LABEL org.opencontainers.image.version="$VERSION"