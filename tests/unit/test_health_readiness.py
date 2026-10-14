import json

from backend.api.routes import health


def test_liveness_is_independent_of_database():
    assert health.health_check() == {
        "status": "healthy",
        "application": "FinTwin API",
    }


def test_database_readiness_returns_503_when_probe_fails(monkeypatch):
    def fail_connect():
        raise ConnectionError("test-only database outage")

    monkeypatch.setattr(health.engine, "connect", fail_connect)
    response = health.database_health_check()
    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "unhealthy",
        "database": "disconnected",
    }


def test_database_readiness_returns_healthy_when_probe_succeeds(monkeypatch):
    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, statement):
            assert str(statement) == "SELECT 1"

    monkeypatch.setattr(health.engine, "connect", lambda: FakeConnection())
    assert health.database_health_check() == {
        "status": "healthy",
        "database": "connected",
    }
