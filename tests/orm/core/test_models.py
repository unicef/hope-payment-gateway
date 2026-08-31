import pytest
from factories import SystemFactory, UserFactory
from hope_payment_gateway.apps.core.models import Singleton


@pytest.fixture
def system():
    return SystemFactory.create(name="Hope")


@pytest.fixture
def test_user():
    return UserFactory.create(username="testuser")


@pytest.mark.django_db
def test_system(system):
    assert str(system) == "Hope"


@pytest.mark.django_db
def test_user_creation(test_user):
    assert test_user.username == "testuser"
    assert test_user._meta.app_label == "core"


def test_singleton():
    class TestSingleton(metaclass=Singleton):
        pass

    s1 = TestSingleton()
    s2 = TestSingleton()
    assert s1 is s2
