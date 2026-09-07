from fastapi.testclient import TestClient

from signaltrade_portfolio.main import app


def test_health_and_ready():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_metrics_are_exposed():
    client = TestClient(app)
    client.get("/does-not-exist/12345")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "signaltrade_http_requests_total" in response.text
    assert 'route="unmatched"' in response.text
    assert "/does-not-exist/12345" not in response.text
