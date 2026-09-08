from __future__ import annotations

from pathlib import Path

import pytest

from services.deep_learn import image_storage


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.no_db
def test_local_image_uses_same_origin_static_url(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(image_storage, "_LOCAL_IMAGE_ROOT", tmp_path)

    url = image_storage._save_local_image(
        "user-1",
        "session-1",
        b"png-bytes",
        "png",
    )

    assert url.startswith("/static/deep_learn_images/user-1/session-1/")
    saved_name = url.rsplit("/", 1)[-1]
    assert (tmp_path / "user-1" / "session-1" / saved_name).read_bytes() == b"png-bytes"


@pytest.mark.no_db
def test_local_images_are_proxied_and_persisted():
    nginx_config = (PROJECT_ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    vite_config = (PROJECT_ROOT / "frontend" / "vite.config.js").read_text(encoding="utf-8")
    compose_config = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "location /static/" in nginx_config
    assert "'/static':" in vite_config
    assert "deep_learn_images:/app/static/deep_learn_images" in compose_config
    assert "deep_learn_images:" in compose_config
