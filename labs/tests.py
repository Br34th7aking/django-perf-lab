import pytest


@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get("/labs/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"