from ..settings import env

AZURE_CLIENT_ID = env("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = env("AZURE_CLIENT_SECRET")
AZURE_TENANT_ID = env("AZURE_TENANT_ID")
SOCIAL_AUTH_AZUREAD_TENANT_OAUTH2_KEY = AZURE_CLIENT_ID
SOCIAL_AUTH_AZUREAD_TENANT_OAUTH2_SECRET = AZURE_CLIENT_SECRET
SOCIAL_AUTH_AZUREAD_TENANT_OAUTH2_TENANT_ID = AZURE_TENANT_ID

SOCIAL_AUTH_URL_NAMESPACE = "social"
SOCIAL_AUTH_SANITIZE_REDIRECTS = False
SOCIAL_AUTH_JSONFIELD_ENABLED = True
SOCIAL_AUTH_USER_MODEL = "core.User"

SOCIAL_AUTH_PIPELINE = (
    "unicef_security.pipeline.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.social_auth.associate_by_email",
    "unicef_security.pipeline.create_unicef_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "hope_payment_gateway.apps.core.pipeline.set_superusers",
)

USER_FIELDS = ["username", "email", "first_name", "last_name"]
USERNAME_IS_FULL_EMAIL = True
