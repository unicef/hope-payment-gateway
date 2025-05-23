# Setup


### System Requirements

- [python](https://www.python.org/)
- [direnv](https://direnv.net/) - not mandatory but strongly recommended
- [uv](https://docs.astral.sh/uv/)
- [postgres](https://www.postgresql.org/)
- [redis](https://redis.io/)


**WARNING**
> Payment Gateway implements **security first** policy. It means that configuration default values are "almost" production compliant.
>
> Es. `DEBUG=False` or `SECURE_SSL_REDIRECT=True`.
>
> Be sure to run `./manage.py env --check` and  `./manage.py env -g all` to check and display your configuration



### 1. Clone repo and install requirements
    git clone https://github.com/unicef/hope-payment-gateway
    uv venv .venv --python 3.13
    source .venv/bin/activate
    uv sync
    pre-commit install

### 2. configure your environment

Uses `./manage.py env` to check required (and optional) variables to put

    ./manage.py env --check


### 3. Run upgrade to run migrations and initial setup

    ./manage.py upgrade
