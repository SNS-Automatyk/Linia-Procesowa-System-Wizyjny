import mimetypes
import os
from typing import Iterable

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


_SRC_DIR = os.path.dirname(__file__)
_PROJECT_DIR = os.path.dirname(_SRC_DIR)


DIST = os.environ.get(
    "DIST_PATH",
    os.path.join(_PROJECT_DIR, "../panel-sterowania/dist"),
)

ANNOTATED_IMAGES_DIR = os.environ.get(
    "ANNOTATED_IMAGES_PATH",
    os.path.join(_PROJECT_DIR, "wizja_zdjecia", "annotated"),
)

_TOP_LEVEL_FILES: Iterable[tuple[str, str]] = (
    ("favicon.ico", "favicon"),
    ("apple-touch-icon.png", "apple-touch-icon"),
    ("android-chrome-192x192.png", "android-chrome-192x192"),
    ("android-chrome-384x384.png", "android-chrome-384x384"),
    ("browserconfig.xml", "browserconfig"),
    ("favicon-16x16.png", "favicon-16x16"),
    ("favicon-32x32.png", "favicon-32x32"),
    ("mstile-150x150.png", "mstile-150x150"),
    ("safari-pinned-tab.svg", "safari-pinned-tab"),
    ("site.webmanifest", "site-webmanifest"),
)


def configure_static(app: FastAPI) -> None:
    mimetypes.add_type("application/manifest+json", ".webmanifest")
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(DIST, "assets")),
        name="assets",
    )

    for filename, route_name in _TOP_LEVEL_FILES:
        app.mount(
            f"/{filename}",
            StaticFiles(directory=DIST),
            name=route_name,
        )

    annotated_path = ANNOTATED_IMAGES_DIR
    try:
        os.makedirs(annotated_path, exist_ok=True)
    except OSError:
        annotated_path = None

    if annotated_path and os.path.isdir(annotated_path):
        app.mount(
            "/annotated-images",
            StaticFiles(directory=annotated_path),
            name="annotated-images",
        )
