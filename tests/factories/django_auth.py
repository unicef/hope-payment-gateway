import factory
from django.contrib.auth.models import Permission

from .base import AutoRegisterModelFactory
from .contenttypes import ContentTypeFactory


class PermissionFactory(AutoRegisterModelFactory):
    content_type = factory.SubFactory(ContentTypeFactory)

    class Meta:
        model = Permission
