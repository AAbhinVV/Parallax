from app.config import Settings


def test_cors_origins_are_normalized() -> None:
    settings = Settings(cors_origins="http://localhost:5173, http://localhost:3000")
    assert settings.cors_origin_list == ["http://localhost:5173", "http://localhost:3000"]


def test_integration_secrets_are_masked() -> None:
    settings = Settings(github_token="super-secret-token")
    assert "super-secret-token" not in repr(settings)
