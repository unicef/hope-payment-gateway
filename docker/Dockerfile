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
    && mkdir -p /code /tmp /data /static \
    && chown -R hpg:hpg /code /tmp /data /static

ENV PACKAGES_DIR=/packages
ENV PYPACKAGES=$PACKAGES_DIR/__pypackages__/3.12
ENV LIB_DIR=$PYPACKAGES/lib
ENV PYTHONPATH=$PYTHONPATH:$LIB_DIR:/code/src
ENV PATH=$PATH:$PYPACKAGES/bin

WORKDIR /code

FROM base as builder

WORKDIR $PACKAGES_DIR
RUN pip install pdm
COPY ../pyproject.toml ./
COPY ../pdm.lock ./
RUN pdm config python.use_venv false
RUN pdm config venv.in_project true
RUN pdm sync --prod --no-editable --no-self

FROM builder AS dev

RUN pdm sync --no-editable --no-self

WORKDIR /code
COPY .. ./

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]


FROM base AS prd

ENV PATH=$PATH:/code/.venv/bin/

COPY --chown=hpg:hpg .. ./
COPY --chown=hpg:hpg --from=builder $PACKAGES_DIR $PACKAGES_DIR
USER hpg

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]