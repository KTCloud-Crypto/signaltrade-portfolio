from fastapi.testclient import TestClient

from signaltrade_portfolio.main import app


def test_health_and_ready():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
