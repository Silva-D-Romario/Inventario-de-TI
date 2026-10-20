import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_check_returns_application_status(client: Client) -> None:
    response = client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {
        "application": "Inventário de TI",
        "version": "0.6.0",
        "status": "UP",
    }


@pytest.mark.django_db
def test_health_check_rejects_post(client: Client) -> None:
    assert client.post("/api/v1/health/").status_code == 405
