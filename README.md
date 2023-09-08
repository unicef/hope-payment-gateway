# Hope Payment Gateway

## How to run

First, prepare your `.env` file. Using `.env.example` should guarantee that you have all the required variables.
```
cp .env.example .env
```

Then, run the following command:
```
docker compose up
```

After that, you can access the API at `http://localhost:8000`.

## How to run tests

The command that runs all static checks and tests would be:
```
docker compose run --rm backend sh -c "isort . && black . && flake8 . && pytest"
```