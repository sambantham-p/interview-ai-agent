import json

from app.core.responses import error_response, success_response


def test_success_response_builds_expected_envelope() -> None:
    response = success_response(data={"foo": "bar"}, status_code=201)

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "success": True,
        "status": "ok",
        "status_code": 201,
        "data": {"foo": "bar"},
    }


def test_success_response_never_includes_error_key() -> None:
    response = success_response()

    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["data"] is None
    assert "error" not in body


def test_error_response_builds_expected_envelope() -> None:
    response = error_response(message="boom", status_code=500)

    assert response.status_code == 500
    assert json.loads(response.body) == {
        "success": False,
        "status": "error",
        "status_code": 500,
        "data": None,
        "error": {"message": "boom"},
    }


def test_error_response_can_carry_extra_data() -> None:
    response = error_response(message="not found", status_code=404, data={"id": "123"})

    body = json.loads(response.body)
    assert body["data"] == {"id": "123"}
