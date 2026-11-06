"""Plane is a connection (Module.active): off until a key and a workspace are saved, so Traverse works without it."""
from core.server import module, settings


def test_plane_is_off_until_it_is_set_up():
    saved = {k: settings.get_all()[k] for k in ("plane.personal_api_key", "plane.workspace_slug")}
    try:
        settings.update({"plane.personal_api_key": "", "plane.workspace_slug": ""})
        assert module.is_active(module.get("plane")) is False
        settings.update({"plane.personal_api_key": "pk-test-12345678", "plane.workspace_slug": "acme"})
        assert module.is_active(module.get("plane")) is True
    finally:
        settings.update(saved)
