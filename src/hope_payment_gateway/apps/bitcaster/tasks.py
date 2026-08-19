from django.contrib.auth import get_user_model

from hope_payment_gateway.apps.bitcaster.client import register_member, unregister_member
from hope_payment_gateway.config.celery import app


@app.task()
def sync_user_to_bitcaster(user_pk: int) -> None:
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_pk)
    except user_model.DoesNotExist:
        return
    register_member(
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
    )


@app.task()
def unregister_user_from_bitcaster(username: str) -> None:
    unregister_member(username)
