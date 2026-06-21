import uuid

import pytest
from django.test import Client

from eingang import health, temporal_client
from eingang.config import Settings
from eingang.problem import PROBLEM_CONTENT_TYPE


def test_healthz_is_always_ok(client: Client) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_database_is_reachable_against_the_test_database() -> None:
    assert health.database_is_reachable(timeout=2.0) is True


@pytest.mark.django_db
def test_readyz_ok_when_database_and_temporal_answer(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health, "temporal_is_reachable", lambda timeout: True)
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "temporal": "ok"}}


@pytest.mark.django_db
def test_readyz_503_names_temporal_when_it_is_down(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health, "temporal_is_reachable", lambda timeout: False)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response["Content-Type"] == PROBLEM_CONTENT_TYPE
    body = response.json()
    assert body["code"] == "NOT_READY"
    assert body["checks"] == {"database": "ok", "temporal": "unreachable"}
    assert "temporal" in body["detail"]


def test_readyz_503_names_the_database_when_it_is_down(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health, "database_is_reachable", lambda timeout: False)
    monkeypatch.setattr(health, "temporal_is_reachable", lambda timeout: True)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "unreachable", "temporal": "ok"}


def test_temporal_health_is_false_for_an_unreachable_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unreachable = Settings(_env_file=None, TEMPORAL_ADDRESS="127.0.0.1:1")
    monkeypatch.setattr(temporal_client, "get_settings", lambda: unreachable)
    assert temporal_client.is_healthy(timeout=2.0) is False


def test_start_processing_raises_when_temporal_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unreachable = Settings(_env_file=None, TEMPORAL_ADDRESS="127.0.0.1:1")
    monkeypatch.setattr(temporal_client, "get_settings", lambda: unreachable)
    temporal_client._get_loop_thread().forget_client()
    with pytest.raises(temporal_client.TemporalUnavailableError):
        temporal_client.start_processing(uuid.uuid4())


def test_signal_never_raises_and_skips_seeded_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    unreachable = Settings(_env_file=None, TEMPORAL_ADDRESS="127.0.0.1:1")
    monkeypatch.setattr(temporal_client, "get_settings", lambda: unreachable)
    temporal_client._get_loop_thread().forget_client()
    temporal_client.signal(uuid.uuid4(), "", "reviewed")  # seeded: nothing to do
    temporal_client.signal(uuid.uuid4(), "invoice-x", "reviewed")  # unreachable: logged only


def test_retry_processing_raises_when_temporal_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unreachable = Settings(_env_file=None, TEMPORAL_ADDRESS="127.0.0.1:1")
    monkeypatch.setattr(temporal_client, "get_settings", lambda: unreachable)
    temporal_client._get_loop_thread().forget_client()
    with pytest.raises(temporal_client.TemporalUnavailableError):
        temporal_client.retry_processing(uuid.uuid4())
