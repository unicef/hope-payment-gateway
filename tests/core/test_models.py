import pytest

from factories import SystemFactory


@pytest.mark.django_db
def test_system():
    system = SystemFactory(name="Hope")
    assert str(system) == "Hope"
