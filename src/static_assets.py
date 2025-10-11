import mimetypes
import os
from typing import Iterable

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


DIST = os.environ.get(
    "DIST_PATH",
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "../panel-sterowania/dist"
    ),
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
