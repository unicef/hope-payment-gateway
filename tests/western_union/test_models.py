import pytest

from factories import CorridorFactory


@pytest.mark.django_db
def test_corridor():
    corridor = CorridorFactory(description="Corridor", template_code="TMP")
    assert str(corridor) == "Corridor / TMP"
