

def test_import_app(monkeypatch):
    # Minimal env for Settings() to load during import.
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://clowbot:clowbot@localhost:5432/clowbot",
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")

    import app.main  # noqa: F401
