FROM python:3.11-slim-bullseye as base


RUN apt-get update \
    && apt-get install -y gcc \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


WORKDIR /tmp

ENV PYTHONPYCACHEPREFIX=/tmp/pycache \
  VIRTUAL_ENV=/opt/venv \
  POETRY_HOME=/opt/poetry \
  PATH=/opt/venv/bin:/opt/poetry/bin:${PATH}

ADD pyproject.toml /tmp
ADD poetry.lock /tmp
RUN python3 -m venv --copies $VIRTUAL_ENV \
  && python3 -m venv --copies $POETRY_HOME \
  && $POETRY_HOME/bin/pip install poetry==1.5.1 \
  && poetry config virtualenvs.create false \
  && poetry config cache-dir /var/cache/poetry

RUN poetry install


WORKDIR /code
ADD . /code

ADD entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]

EXPOSE 8000


### TODO: for dist target, use poetry install --without dev