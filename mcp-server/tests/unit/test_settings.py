from app.settings import load_settings


def test_load_settings_reads_download_nvr_configuration(monkeypatch):
    monkeypatch.setenv("HCNETSDK_DOWNLOAD_NVR_HOSTS", "10.10.7.252, 10.10.7.253")
    monkeypatch.setenv("HCNETSDK_DOWNLOAD_PORT", "8000")
    monkeypatch.setenv("HCNETSDK_DOWNLOAD_USERNAME", "admin")
    monkeypatch.setenv("HCNETSDK_DOWNLOAD_PASSWORD", "secret-from-env")
    monkeypatch.setenv("HCNETSDK_DOWNLOAD_CHANNEL", "1")

    settings = load_settings()

    assert settings.hcnetsdk_download_nvr_hosts == ("10.10.7.252", "10.10.7.253")
    assert settings.hcnetsdk_download_port == 8000
    assert settings.hcnetsdk_download_username == "admin"
    assert settings.hcnetsdk_download_password == "secret-from-env"
    assert settings.hcnetsdk_download_channel == 1
