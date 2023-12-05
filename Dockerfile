FROM python:3.11-slim-bullseye as base

RUN apt-get update \
    && apt-get install -y \
        gcc curl libgdal-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && addgroup --system --gid 82 hpg \
    && adduser \
        --system --uid 82 \
        --disabled-password --home /home/hpg \
        --shell /sbin.nologin --group hpg --gecos hpg \
    && mkdir -p /code /tmp /data /static \
    && chown -R hpg:hpg /code /tmp /data /static

ENV PACKAGES_DIR=/packages
ENV VIRTUAL_ENV=$PACKAGES_DIR/.venv/lib/python3.11/site-packages
ENV PYTHONPYCACHEPREFIX=/tmp/pycache
ENV PYTHONPATH=$PYTHONPATH:$VIRTUAL_ENV:/code/src
ENV PATH=$PATH:$PACKAGES_DIR/.venv/bin/

WORKDIR /code

FROM base as builder

WORKDIR $PACKAGES_DIR
RUN pip install pdm==2.9.3
ADD pyproject.toml ./
ADD pdm.lock ./
RUN pdm sync --prod --no-editable --no-self

FROM builder AS dev

RUN pdm sync --no-editable --no-self

WORKDIR /code
COPY ./ ./

ADD entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]


FROM base AS prd

ENV PATH=$PATH:/code/.venv/bin/

COPY --chown=hpg:hpg ./ ./
COPY --chown=hpg:hpg --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
USER hpg

ADD entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]