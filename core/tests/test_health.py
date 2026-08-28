from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.test import Client


def test_health_returns_ok(client: Client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_returns_ready_when_database_responds(client: Client) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_returns_503_when_database_is_unavailable(client: Client) -> None:
    with patch("core.views.connection.cursor", side_effect=DatabaseError):
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}

