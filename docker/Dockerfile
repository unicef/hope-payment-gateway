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

ENV PACKAGES_DIR=/packages
ENV PYTHONPATH=$PYTHONPATH:$LIB_DIR:/app/src
ENV PATH=$PATH:$PYPACKAGES/bin

WORKDIR /app

FROM base as builder

WORKDIR $PACKAGES_DIR
COPY uv.lock README.md MANIFEST.in pyproject.toml /app/
RUN pip install uv

RUN --mount=type=cache,target=/root/.uv-cache \
    --mount=type=bind,source=uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml \
    --mount=type=bind,source=MANIFEST.in,target=/app/MANIFEST.in \
    --mount=type=bind,source=./src/hope_payment_gateway,target=/app/src/hope_payment_gateway \
    uv sync --cache-dir=/root/.uv-cache --no-dev --no-editable --frozen --extra distribution

FROM builder AS dev

RUN --mount=type=cache,target=/root/.uv-cache \
    --mount=type=bind,source=uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml \
    --mount=type=bind,source=MANIFEST.in,target=/app/MANIFEST.in \
    --mount=type=bind,source=./src/hope_payment_gateway,target=/app/src/hope_payment_gateway \
    uv sync --cache-dir=/root/.uv-cache --no-editable --frozen --extra distribution \


WORKDIR /app
COPY .. ./

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]


FROM base AS prd

ENV PATH=$PATH:/app/.venv/bin/
RUN pip install uv uwsgi

COPY --chown=hpg:hpg .. ./
COPY --chown=hpg:hpg --from=builder $PACKAGES_DIR $PACKAGES_DIR
USER hpg

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]