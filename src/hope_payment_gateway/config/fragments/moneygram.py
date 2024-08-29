from ..settings import env

# production: https://api.moneygram.com
# test: https://sandboxapi.moneygram.com

MONEYGRAM_HOST = env("MONEYGRAM_HOST", default="")
MONEYGRAM_CLIENT_ID = env("MONEYGRAM_CLIENT_ID", default="")
MONEYGRAM_CLIENT_SECRET = env("MONEYGRAM_CLIENT_SECRET", default="")
MONEYGRAM_PARTNER_ID = env("MONEYGRAM_PARTNER_ID", default="")
