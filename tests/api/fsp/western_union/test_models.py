import pytest
from factories import CorridorFactory


@pytest.fixture
def corridor():
    return CorridorFactory.create(description="Corridor", template_code="TMP")


@pytest.mark.django_db
def test_corridor(corridor):
    assert str(corridor) == "Corridor / TMP"
