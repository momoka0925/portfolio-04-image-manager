import os

from fastapi.testclient import TestClient

from tests.conftest import make_png


def _upload(client: TestClient, content: bytes, filename="a.png", ctype="image/png"):
    return client.post("/images", files={"file": (filename, content, ctype)})


def test_upload_success(client: TestClient) -> None:
    res = _upload(client, make_png())
    assert res.status_code == 201, res.text
    data = res.json()["data"]
    assert data["width"] == 100 and data["height"] == 80
    assert data["content_type"] == "image/png"
    assert len(data["sha256"]) == 64
    assert data["status"] == "PENDING"


def test_duplicate_returns_existing_200(client: TestClient) -> None:
    png = make_png()
    first = _upload(client, png).json()["data"]
    res = _upload(client, png, filename="other.png")
    assert res.status_code == 200  # 重複は既存を返す
    assert res.json()["data"]["id"] == first["id"]


def test_reject_non_image_with_image_header(client: TestClient) -> None:
    # image/png を名乗るが中身はテキスト → Pillowで弾く
    res = _upload(client, b"this is not an image", filename="fake.png", ctype="image/png")
    assert res.status_code == 400


def test_reject_extension_mime_mismatch(client: TestClient) -> None:
    res = _upload(client, make_png(), filename="a.jpg", ctype="image/png")
    assert res.status_code == 400


def test_reject_unsupported_type(client: TestClient) -> None:
    res = _upload(client, b"%PDF-1.4", filename="a.pdf", ctype="application/pdf")
    assert res.status_code == 400


def test_reject_too_large(client: TestClient) -> None:
    # conftestのmax_bytesは1MB。サイズ超過はストリーム中に検出され、Pillow検証より先に413になる。
    # 単色PNGは圧縮で小さくなるため、非圧縮なランダムbytesで確実に上限超過させる。
    big = b"\x89PNG\r\n\x1a\n" + os.urandom(1024 * 1024 + 1000)
    assert len(big) > 1024 * 1024
    res = _upload(client, big)
    assert res.status_code == 413


def test_list_and_pagination(client: TestClient) -> None:
    for i in range(3):
        _upload(client, make_png(color=(i * 10, 0, 0)), filename=f"{i}.png")
    data = client.get("/images?page=1&limit=2").json()["data"]
    assert data["total"] == 3
    assert len(data["items"]) == 2


def test_list_sort_size_asc(client: TestClient) -> None:
    _upload(client, make_png(size=(50, 50)), filename="small.png")
    _upload(client, make_png(size=(300, 300)), filename="big.png")
    items = client.get("/images?sort=size&order=asc").json()["data"]["items"]
    assert items[0]["size"] <= items[1]["size"]


def test_get_and_file_and_delete(client: TestClient) -> None:
    img = _upload(client, make_png()).json()["data"]
    assert client.get(f"/images/{img['id']}").status_code == 200
    f = client.get(f"/images/{img['id']}/file")
    assert f.status_code == 200 and f.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.delete(f"/images/{img['id']}").status_code == 200
    assert client.get(f"/images/{img['id']}").status_code == 404
    assert client.get("/images").json()["data"]["total"] == 0


def test_get_missing_404(client: TestClient) -> None:
    assert client.get("/images/999").status_code == 404
