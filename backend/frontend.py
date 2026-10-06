"""Serve only the built public frontend; API misses must never return SPA HTML."""
from pathlib import Path
import mimetypes
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles


def install_frontend(app, directory):
    # Windows registry mappings can omit modern web media types.
    for extension, media_type in {".webp": "image/webp", ".woff2": "font/woff2", ".js": "text/javascript", ".css": "text/css"}.items():
        mimetypes.add_type(media_type, extension)
    directory = Path(directory).resolve(strict=True)
    index = directory / "index.html"
    if not index.is_file():
        raise RuntimeError("Build the frontend before enabling FRONTEND_DIST")
    app.mount("/assets", StaticFiles(directory=directory / "assets"), name="frontend-assets")
    app.mount("/images", StaticFiles(directory=directory / "images"), name="frontend-images")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def frontend(request: Request, path: str):
        if path == "favicon.svg":
            return FileResponse(directory / path, headers={"Cache-Control": "public, max-age=3600"})
        route = path.split("/", 1)[0]
        if route in {"api", "docs", "redoc", "openapi.json"}:
            raise HTTPException(404, "Not found")
        if "." in path or "\\" in path:
            raise HTTPException(404, "Not found")
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
