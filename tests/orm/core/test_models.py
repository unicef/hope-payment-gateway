import pytest
from factories import SystemFactory, UserFactory
from hope_payment_gateway.apps.core.models import Singleton


@pytest.mark.django_db
def test_system():
    system = SystemFactory(name="Hope")
    assert str(system) == "Hope"


@pytest.mark.django_db
def test_user_creation():
    user = UserFactory(username="testuser")
    assert user.username == "testuser"
    assert user._meta.app_label == "core"


def test_singleton():
    class TestSingleton(metaclass=Singleton):
        pass

    s1 = TestSingleton()
    s2 = TestSingleton()
    assert s1 is s2
