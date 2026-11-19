"""Unit tests for the order of checks, tracing metadata and the web page."""

from conftest import ALICE_KEY, FakeClock

QUESTION = {"question": "Who is PRD-0004?"}


def test_invalid_key_wins_over_an_invalid_body(make_client):
    client = make_client(key="wrong-key")
    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid or missing API key"}


def test_rejected_keys_do_not_use_up_the_quota(make_client):
    clock = FakeClock()
    anonymous = make_client(key=None, clock=clock, RATE_LIMIT_PER_MINUTE=2)
    for _ in range(5):
        assert anonymous.post("/ask", json=QUESTION).status_code == 401
    valid = make_client(clock=clock, RATE_LIMIT_PER_MINUTE=2)
    assert valid.post("/ask", json=QUESTION).status_code == 200


def test_trace_metadata_names_the_client_and_never_the_key(
    make_client, fake_langsmith, monkeypatch
):
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-secret-value-123456")
    client = make_client(LANGSMITH_TRACING="true")
    assert client.post("/ask", json=QUESTION).status_code == 200
    assert fake_langsmith.extras
    for extra in fake_langsmith.extras:
        assert extra["metadata"]["client"] == "alice"
    assert ALICE_KEY not in str(fake_langsmith.extras)


def test_home_page_asks_for_the_key_and_keeps_it_in_session_storage(client):
    page = client.get("/").text
    assert 'data-testid="api-key"' in page
    assert 'type="password"' in page
    assert "sessionStorage" in page
    assert "localStorage" not in page
    assert "X-API-Key" in page
    assert "Clave inválida" in page
    assert "Demasiadas preguntas; espera" in page
    assert ALICE_KEY not in page
