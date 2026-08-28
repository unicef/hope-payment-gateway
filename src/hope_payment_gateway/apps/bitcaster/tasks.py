from celery import shared_task
from django.contrib.auth import get_user_model

from hope_payment_gateway.apps.bitcaster.client import get_hope_bitcaster_client


@shared_task()
def sync_user_to_bitcaster(user_pk: int) -> None:
    client = get_hope_bitcaster_client()
    if client is None:
        return
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_pk)
    except user_model.DoesNotExist:
        return
    client.register_user(user)


@shared_task()
def unregister_user_from_bitcaster(username: str) -> None:
    client = get_hope_bitcaster_client()
    if client is None:
        return
    client.unregister_user(username)
