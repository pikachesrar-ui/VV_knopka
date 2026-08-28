import httpx

from vv_knopka.openai_auth import safe_openai_error


def test_401_error_is_helpful_and_redacts_key():
    response = httpx.Response(
        401,
        json={
            "error": {
                "code": "invalid_api_key",
                "message": "Incorrect API key provided: sk-proj-super-secret-value",
            }
        },
    )
    message = safe_openai_error(response)
    assert "401" in message
    assert "invalid_api_key" in message
    assert "super-secret-value" not in message
    assert "OPENAI_API_KEY" in message
