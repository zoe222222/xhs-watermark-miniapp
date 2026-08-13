import base64
import json
import os
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib import error
from urllib.parse import urlparse

# 最多同时 3 个线程做 Pillow 图片转换，防止 OOM
_IMG_SEMAPHORE = threading.Semaphore(3)

from xhs_fetcher import fetch_images, proxy_image

# 允许代理的图片域名白名单（防止 SSRF）
_ALLOWED_IMG_HOSTS = {
    "ci.xiaohongshu.com",
    "sns-webpic-qc.xhscdn.com",
    "sns-img-qc.xhscdn.com",
    "sns-img-hw.xhscdn.com",
    "sns-img-bd.xhscdn.com",
    "xhscdn.com",
}

MAX_BODY_SIZE = 20 * 1024 * 1024  # 20 MB，防止超大请求撑爆内存

# local_model 延迟导入：只有真正调用去水印时才加载，避免启动时报错
_LocalWatermarkModel = None
def _get_local_model_class():
    global _LocalWatermarkModel
    if _LocalWatermarkModel is None:
        from local_model import LocalWatermarkModel
        _LocalWatermarkModel = LocalWatermarkModel
    return _LocalWatermarkModel


HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", os.environ.get("WATERMARK_BACKEND_PORT", "8787")))

def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


class WatermarkBackend:
    def __init__(self):
        self.provider = os.environ.get("WATERMARK_PROVIDER", "local").strip().lower()
        self.model_path = os.environ.get(
            "LOCAL_WATERMARK_MODEL_PATH",
            str(Path(__file__).resolve().parent / "models" / "big-lama.safetensors"),
        )
        self.local_model = None

    def health(self):
        return {
            "provider": self.provider or "unconfigured",
            "configured": self.provider == "local" and Path(self.model_path).exists(),
            "modelPath": self.model_path,
        }

    def remove(self, image_b64, mime_type):
        if self.provider == "local":
            return self._remove_with_local_model(image_b64, mime_type)
        raise RuntimeError(f"暂不支持的 provider: {self.provider}")

    def _remove_with_local_model(self, image_b64, mime_type):
        if self.local_model is None:
            self.local_model = _get_local_model_class()(self.model_path)

        from PIL import Image

        image_bytes = base64.b64decode(image_b64)
        pil_image = Image.open(BytesIO(image_bytes)).convert("RGB")
        result = self.local_model.run(pil_image)

        output = BytesIO()
        result.save(output, format="PNG")
        encoded = base64.b64encode(output.getvalue()).decode("utf-8")
        return {
            "imageBase64": encoded,
            "mimeType": "image/png",
            "summary": "本地模型已自动完成去水印处理",
        }


BACKEND = WatermarkBackend()


def build_version_payload():
    git_commit = (
        os.environ.get("RAILWAY_GIT_COMMIT_SHA")
        or os.environ.get("GIT_COMMIT_SHA")
        or os.environ.get("COMMIT_SHA")
        or "local"
    )
    if len(git_commit) > 12:
        git_commit = git_commit[:12]

    return {
        "ok": True,
        "service": "xhs-watermark-backend",
        "gitCommit": git_commit,
        "provider": BACKEND.provider or "unconfigured",
        "configured": BACKEND.health()["configured"],
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默日志

    def do_OPTIONS(self):
        json_response(self, 200, {"ok": True})

    # ── GET ──────────────────────────────────────────────────────────────────

    def do_GET(self):
        path_qs = self.path.split("?", 1)
        path = path_qs[0]
        qs   = urllib.parse.parse_qs(path_qs[1]) if len(path_qs) > 1 else {}

        if path == "/api/health":
            json_response(self, 200, {"ok": True, "backend": BACKEND.health()})
            return

        if path == "/api/version":
            json_response(self, 200, build_version_payload())
            return

        # 图片代理端点：/api/proxy-image?url=...&filename=...
        if path == "/api/proxy-image":
            self._handle_proxy_image(qs)
            return

        if path in ("/", ""):
            json_response(self, 200, build_version_payload())
            return

        json_response(self, 404, {"ok": False, "error": "Not found"})

    def _handle_proxy_image(self, qs):
        urls = qs.get("url", [])
        if not urls:
            json_response(self, 400, {"ok": False, "error": "缺少 url 参数"})
            return
        target_url = urllib.parse.unquote(urls[0])

        # SSRF 防护：只允许白名单域名
        try:
            parsed_host = urlparse(target_url).hostname or ""
        except Exception:
            parsed_host = ""
        allowed = any(
            parsed_host == h or parsed_host.endswith("." + h)
            for h in _ALLOWED_IMG_HOSTS
        )
        if not allowed:
            json_response(self, 403, {"ok": False, "error": "不允许的图片域名"})
            return

        fmt   = qs.get("fmt",   [""])[0].lower()   # fmt=png  → 转为 PNG
        thumb = qs.get("thumb", [""])[0] == "1"     # thumb=1  → 缩略图

        try:
            data, content_type = proxy_image(target_url)
        except Exception as e:
            json_response(self, 502, {"ok": False, "error": f"图片下载失败: {e}"})
            return

        # 缩略图模式：等比缩放到宽 800px，JPEG q=82，大幅减小体积加快加载
        if thumb:
            with _IMG_SEMAPHORE:
                try:
                    from PIL import Image
                    img = Image.open(BytesIO(data)).convert("RGB")
                    w, h = img.size
                    if w > 800:
                        img = img.resize((800, int(h * 800 / w)), Image.LANCZOS)
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=82, optimize=True)
                    data = buf.getvalue()
                    content_type = "image/jpeg"
                except Exception:
                    pass  # 转换失败则返回原始数据

        # fmt=png：强制转换为 PNG（解决 iOS saveImageToPhotosAlbum 不支持 WebP 的问题）
        elif fmt == "png" and content_type != "image/png":
            with _IMG_SEMAPHORE:
                try:
                    from PIL import Image
                    img = Image.open(BytesIO(data)).convert("RGB")
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    data = buf.getvalue()
                    content_type = "image/png"
                except Exception:
                    pass  # 转换失败则返回原始数据

        filename = "image.png" if content_type == "image/png" else "image.jpg"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    # ── POST ─────────────────────────────────────────────────────────────────

    def do_POST(self):
        path = self.path.split("?")[0]

        if path == "/api/fetch-xhs":
            self._handle_fetch_xhs()
            return

        if path == "/api/remove-watermark":
            self._handle_remove_watermark()
            return

        json_response(self, 404, {"ok": False, "error": "Not found"})

    def _handle_fetch_xhs(self):
        try:
            length = min(int(self.headers.get("Content-Length", "0")), MAX_BODY_SIZE)
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            link = payload.get("link", "").strip()
            if not link:
                json_response(self, 400, {"ok": False, "error": "缺少 link 参数"})
                return

            result = fetch_images(link)
            status = 200 if result.get("ok") else 422
            json_response(self, status, result)
        except (ValueError, KeyError) as exc:
            json_response(self, 400, {"ok": False, "error": f"请求格式错误: {exc}"})
        except Exception as exc:
            json_response(self, 500, {"ok": False, "error": f"服务异常: {exc}"})

    def _handle_remove_watermark(self):
        try:
            length = min(int(self.headers.get("Content-Length", "0")), MAX_BODY_SIZE)
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            image_b64 = payload.get("imageBase64", "")
            mime_type  = payload.get("mimeType", "image/png")
            if not image_b64:
                json_response(self, 400, {"ok": False, "error": "缺少 imageBase64"})
                return

            result = BACKEND.remove(image_b64, mime_type)
            json_response(self, 200, {"ok": True, **result})
        except RuntimeError as exc:
            json_response(self, 400, {"ok": False, "error": str(exc)})
        except (ValueError, KeyError, TypeError) as exc:
            json_response(self, 400, {"ok": False, "error": f"请求格式错误: {exc}"})
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="ignore")
            json_response(self, 502, {"ok": False, "error": f"模型服务错误: {message}"})
        except Exception as exc:
            json_response(self, 500, {"ok": False, "error": f"服务异常: {exc}"})


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"watermark backend listening on http://{HOST}:{PORT}")
    server.serve_forever()
