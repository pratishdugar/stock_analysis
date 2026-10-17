import config


def test_gemini_not_configured_without_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert not config.gemini_configured()


def test_gemini_configured_with_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    monkeypatch.setenv("GEMINI_MODEL", "some-model")
    assert config.gemini_configured()


def test_weights_sum_to_one():
    assert abs(config.QUANT_WEIGHT + config.NEWS_WEIGHT - 1.0) < 1e-9
