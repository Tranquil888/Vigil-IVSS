from vigil.telemetry.redaction import redact_text


def test_camera_credentials_are_removed():
    text = "connecting to rtsp://admin:hunter2@10.0.0.5:554/sub"
    cleaned = redact_text(text)
    assert "hunter2" not in cleaned
    assert "admin" not in cleaned
    assert "rtsp://10.0.0.5:554/sub" in cleaned


def test_bearer_token_is_removed():
    cleaned = redact_text("Authorization: Bearer abc.def.ghi")
    assert "abc.def.ghi" not in cleaned
    assert "[redacted]" in cleaned


def test_password_assignment_is_removed():
    cleaned = redact_text("password=letmein token: 12345 api_key=zzz")
    assert "letmein" not in cleaned
    assert "12345" not in cleaned
    assert "zzz" not in cleaned


def test_embedding_vector_is_omitted():
    vector = "[" + ", ".join("%.6f" % (i / 100.0) for i in range(128)) + "]"
    cleaned = redact_text("embedding=" + vector)
    assert "omitted" in cleaned
    assert "0.000000" not in cleaned


def test_plain_text_is_untouched():
    assert redact_text("camera front started") == "camera front started"
