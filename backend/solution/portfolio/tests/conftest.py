import pytest

from portfolio.fx_service import reset_cache


@pytest.fixture(autouse=True)
def fresh_fx_cache():
    """The FX rate cache is process-wide; isolate every test from it."""
    reset_cache()
    yield
    reset_cache()
