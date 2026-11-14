import sys
from pathlib import Path

import pytest

# Make `backend`, `ml` and `database` importable when pytest runs from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A test client on a fresh, empty database (seeded with the sample project at startup)."""
    monkeypatch.setenv("QBI_DB", str(tmp_path / "test.db"))
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as c:
        yield c
