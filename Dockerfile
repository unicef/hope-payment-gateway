FROM python:3.11-slim-bullseye as base

RUN apt-get update \
    && apt-get install -y \
        gcc curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && addgroup --system --gid 82 hpg \
    && adduser \
        --system --uid 82 \
        --disabled-password --home /home/hpg \
        --shell /sbin.nologin --group hpg --gecos hpg \
    && mkdir -p /code /tmp /data \
    && chown -R hpg:hpg /code /tmp /data

ENV PYTHONPYCACHEPREFIX=/tmp/pycache \
  VIRTUAL_ENV=/opt/venv \
  POETRY_HOME=/opt/poetry \
  PATH=/opt/venv/bin:/opt/poetry/bin:${PATH}


FROM base as builder

WORKDIR /tmp
ADD pyproject.toml /tmp
ADD poetry.lock /tmp
RUN python3 -m venv --copies $VIRTUAL_ENV \
  && python3 -m venv --copies $POETRY_HOME \
  && $POETRY_HOME/bin/pip install poetry==1.5.1 \
  && poetry config virtualenvs.create false \
  && poetry config cache-dir /var/cache/poetry
RUN poetry install --without dev


FROM builder AS dev

RUN poetry install
COPY ./ ./

ADD entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]


FROM base AS prd

COPY --chown=hpg:hpg ./ ./
COPY --chown=hpg:hpg --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
USER hpg

ADD entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]