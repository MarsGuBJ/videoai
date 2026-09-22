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


def _clear_device_env(monkeypatch):
    monkeypatch.delenv("HCNETSDK_DOWNLOAD_NVR_HOSTS", raising=False)
    monkeypatch.delenv("CVR_HOSTS", raising=False)


def test_device_defaults_follow_10_segment(monkeypatch):
    """10 网段部署（MCP 对外基址 10.*）：默认只用 10.10 NVR，不配 CVR。"""
    _clear_device_env(monkeypatch)
    monkeypatch.setenv("VIDEOAI_MCP_PUBLIC_BASE_URL", "http://10.10.3.100:8097")

    settings = load_settings()

    assert settings.hcnetsdk_download_nvr_hosts == ("10.10.7.252", "10.10.7.253")
    assert settings.cvr_hosts == ()


def test_device_defaults_follow_172_segment(monkeypatch):
    """172 网段部署（MCP 对外基址 172.*）：默认只用 172 CVR，不配 NVR 白名单。"""
    _clear_device_env(monkeypatch)
    monkeypatch.setenv("VIDEOAI_MCP_PUBLIC_BASE_URL", "http://172.17.136.189:8097")

    settings = load_settings()

    assert settings.hcnetsdk_download_nvr_hosts == ()
    assert settings.cvr_hosts == ("172.21.200.21", "172.21.200.22", "172.21.200.23")


def test_device_defaults_fall_back_to_legacy_on_unknown_segment(monkeypatch):
    """未知网段（域名/本机地址）：保持历史默认（NVR+CVR 全配），避免新环境起不来。"""
    _clear_device_env(monkeypatch)
    monkeypatch.setenv("VIDEOAI_MCP_PUBLIC_BASE_URL", "http://mcp.example.com:8097")

    settings = load_settings()

    assert settings.hcnetsdk_download_nvr_hosts == ("10.10.7.252", "10.10.7.253")
    assert settings.cvr_hosts == ("172.21.200.21", "172.21.200.22", "172.21.200.23")


def test_explicit_device_hosts_override_segment_default(monkeypatch):
    """显式配置优先于网段默认；显式置空等同于未设置（用网段默认）。"""
    _clear_device_env(monkeypatch)
    monkeypatch.setenv("VIDEOAI_MCP_PUBLIC_BASE_URL", "http://10.10.3.100:8097")
    monkeypatch.setenv("CVR_HOSTS", "10.9.9.9, 10.9.9.10")

    settings = load_settings()

    assert settings.cvr_hosts == ("10.9.9.9", "10.9.9.10")
    assert settings.hcnetsdk_download_nvr_hosts == ("10.10.7.252", "10.10.7.253")

    monkeypatch.setenv("CVR_HOSTS", "")
    settings = load_settings()
    assert settings.cvr_hosts == ()
