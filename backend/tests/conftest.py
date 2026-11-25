import pytest

from app.services.postal_codes import clear_postal_code_cache


@pytest.fixture(autouse=True)
def _isolated_postal_code_cache():
    clear_postal_code_cache()
    yield
    clear_postal_code_cache()
