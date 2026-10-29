import json

from aiohttp import ClientTimeout, ConnectionTimeoutError
from pathlib import Path
from arclet.entari import Startup, Entari, listen


INDEX_ = "https://raw.githubusercontent.com/fraqjs/qq-faces/refs/heads/main/faces.json"
INDEX_URL_PROXIED = "https://ghfast.top/github.com/fraqjs/qq-faces/refs/heads/main/faces.json"

root = Path(__file__).parent
faces = root / "assets" / "faces.json"


@listen(Startup)
async def init_faces(app: Entari):
    if faces.exists():
        return

    try:
        async with app.http.get(INDEX_, timeout=ClientTimeout(connect=10), allow_redirects=True) as resp:
            if resp.status == 200:
                data = await resp.text()
                faces.parent.mkdir(parents=True, exist_ok=True)
                with faces.open("w", encoding="utf-8") as f:
                    f.write(data)
    except ConnectionTimeoutError:
        try:
            async with app.http.get(INDEX_URL_PROXIED, timeout=ClientTimeout(connect=10), allow_redirects=True) as resp:
                if resp.status == 200:
                    data = await resp.text()
                    faces.parent.mkdir(parents=True, exist_ok=True)
                    with faces.open("w", encoding="utf-8") as f:
                        f.write(data)
        except Exception:
            pass


def query(face_id: str) -> dict | None:
    if not faces.exists():
        return None
    with faces.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(face_id)
