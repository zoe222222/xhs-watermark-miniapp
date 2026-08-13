"""
小红书帖子图片提取器
支持：
  • https://www.xiaohongshu.com/explore/NOTE_ID
  • https://www.xiaohongshu.com/discovery/item/NOTE_ID
  • http://xhslink.com/XXXX  （自动跟随重定向）
  • 任何包含上述链接的分享文本
"""
import json
import re
import subprocess
import urllib.request
import urllib.parse
from typing import Optional, List, Tuple
from urllib.error import URLError, HTTPError

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


# ── URL 工具 ────────────────────────────────────────────────────────────────

def extract_note_url(text: str) -> Optional[str]:
    """从任意文本中提取小红书帖子 URL（支持短链）。"""
    patterns = [
        r"https?://www\.xiaohongshu\.com/(?:explore|discovery/item)/[0-9a-f]+[^\s\"'<>]*",
        r"https?://xhslink\.com/[^\s\"'<>]+",
        r"http://xhslink\.com/[^\s\"'<>]+",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return None


def _resolve_short_url(url: str, timeout: int = 12) -> str:
    """
    跟随短链重定向，只捕获第一次 3xx Location，不下载最终页面。
    xhslink.com 必须用 GET（HEAD 返回 404）。
    抛出 StopIteration 来中断后续重定向，从而避免下载最终目标页面。
    """
    captured = [url]

    class _StopAfterFirst(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            captured[0] = newurl
            # 返回 None 阻止继续跟随重定向
            return None

    opener = urllib.request.build_opener(_StopAfterFirst)
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with opener.open(req, timeout=timeout):
            pass
    except Exception:
        pass  # 无论如何都检查 captured

    if captured[0] != url:
        return captured[0]
    raise RuntimeError(f"未能解析短链重定向: {url}")


def fetch_page(url: str, timeout: int = 20) -> Tuple[str, str]:
    """
    下载页面 HTML，返回 (最终URL, html)。
    使用 curl 子进程绕过 TLS 指纹检测（Python urllib 会被小红书封锁）。
    """
    cmd = [
        "curl", "-sL",
        "--max-time", str(timeout),
        "-H", f"User-Agent: {_UA}",
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "-H", "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
        "-H", "Referer: https://www.xiaohongshu.com/",
        "--write-out", "\n__FINAL_URL__:%{url_effective}",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
    if result.returncode != 0:
        raise RuntimeError(f"curl 失败 (exit {result.returncode}): {result.stderr.decode('utf-8', errors='replace')[:200]}")

    raw = result.stdout.decode("utf-8", errors="replace")
    # 从末尾分离 final url 标记
    if "\n__FINAL_URL__:" in raw:
        body, marker = raw.rsplit("\n__FINAL_URL__:", 1)
        final_url = marker.strip() or url
    else:
        body = raw
        final_url = url

    return final_url, body


def _normalise_url(url: str) -> str:
    """
    统一化图片 URL：提取图片路径，转换为 ci.xiaohongshu.com 格式。
    ci.xiaohongshu.com 无防盗链限制，可直接在浏览器加载/下载。

    支持两种 CDN 路径格式：
      旧格式: /TIMESTAMP/HASH/IMAGE_ID
      新格式: /TIMESTAMP/HASH/notes_pre_post/IMAGE_ID
    """
    if url.startswith("//"):
        url = "https:" + url
    # 移除 query 和 !格式后缀
    url = url.split("?")[0]
    url = re.sub(r"![^/]*$", "", url).rstrip("/")

    # 匹配新格式：含 notes_pre_post/ 子路径
    m = re.search(r'(notes_pre_post/[0-9a-zA-Z]+)$', url)
    if m:
        return f"https://ci.xiaohongshu.com/{m.group(1)}"

    # 匹配旧格式：末尾直接是图片 ID
    image_id = url.rsplit("/", 1)[-1]
    if image_id and re.match(r'^[0-9a-zA-Z]{20,}$', image_id):
        return f"https://ci.xiaohongshu.com/{image_id}"

    return url


# ── 解析策略 ────────────────────────────────────────────────────────────────

def _parse_images(html: str) -> List[dict]:
    """
    从页面 HTML 提取图片列表。
    小红书把 URL 用 \\u002F 转义存在 JSON 中；先 unescape，再提取。
    优先取 WB_DFT（高质量默认图），无则取所有 sns-webpic/sns-img URL。
    """
    # unicode_escape 解码：把 \u002F → /
    try:
        unescaped = html.encode("raw_unicode_escape").decode("unicode_escape", errors="replace")
    except Exception:
        unescaped = html

    # ── 策略1：提取 WB_DFT 场景的图片（最高质量） ─────────────────────────
    dft_urls = []
    for m in re.finditer(r'"imageScene"\s*:\s*"WB_DFT"\s*,\s*"url"\s*:\s*"([^"]+)"', unescaped):
        u = _normalise_url(m.group(1))
        if "ci.xiaohongshu.com/" in u and u not in dft_urls:
            dft_urls.append(u)

    if dft_urls:
        return [{"url": u, "width": 0, "height": 0} for u in dft_urls]

    # ── 策略2：提取所有 sns-webpic/sns-img URL ──────────────────────────────
    img_urls = []
    for m in re.finditer(r'https?://sns-(?:webpic|img)[^\s"\'<>!]+', unescaped):
        u = _normalise_url(m.group(0))
        # 过滤掉转换失败的空 CDN 域名（无图片 ID）
        if u and "ci.xiaohongshu.com/" in u and u not in img_urls:
            img_urls.append(u)

    if img_urls:
        return [{"url": u, "width": 0, "height": 0} for u in img_urls]

    # ── 策略3：og:image 回退 ────────────────────────────────────────────────
    for pattern in [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ]:
        m = re.search(pattern, html)
        if m:
            u = _normalise_url(m.group(1))
            return [{"url": u, "width": 0, "height": 0}]

    return []


# ── 公开接口 ────────────────────────────────────────────────────────────────

def fetch_images(raw_input: str) -> dict:
    """
    主入口。接受用户粘贴的文本（URL 或含 URL 的分享文字）。
    返回：
        {"ok": True,  "images": [...], "total": N, "sourceUrl": "..."}
        {"ok": False, "error": "..."}
    """
    url = extract_note_url(raw_input)
    if not url:
        if raw_input.strip().startswith("http"):
            url = raw_input.strip()
        else:
            return {"ok": False, "error": "未能识别小红书帖子链接，请粘贴完整 URL 或分享文本"}

    # 若是短链，先解析重定向目标
    if "xhslink.com" in url:
        try:
            url = _resolve_short_url(url, timeout=12)
        except Exception as e:
            return {"ok": False, "error": f"短链解析失败：{e}"}

    # 下载页面
    try:
        final_url, html = fetch_page(url, timeout=20)
    except (URLError, HTTPError) as e:
        return {"ok": False, "error": f"页面请求失败：{e}"}
    except Exception as e:
        return {"ok": False, "error": f"未知错误：{e}"}

    if "请登录" in html or "/login" in final_url:
        return {"ok": False, "error": "该帖子需要登录才能查看，暂不支持"}

    images = _parse_images(html)

    if not images:
        return {"ok": False, "error": "未能从页面中提取到图片，可能帖子结构已变化"}

    for i, img in enumerate(images):
        img["index"] = i

    return {"ok": True, "images": images, "total": len(images), "sourceUrl": final_url}


def proxy_image(url: str, timeout: int = 20) -> Tuple[bytes, str]:
    """代理下载一张图片，返回 (图片字节, content-type)。使用 curl 避免被拦截。"""
    cmd = [
        "curl", "-sL",
        "--max-time", str(timeout),
        "-H", f"User-Agent: {_UA}",
        "-H", "Accept: image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "-H", "Referer: https://www.xiaohongshu.com/",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
    if result.returncode != 0:
        raise RuntimeError(f"curl 失败: {result.stderr.decode('utf-8', errors='replace')[:200]}")

    data = result.stdout
    if not data:
        raise RuntimeError("图片内容为空")

    # 根据文件头判断图片类型
    ct = "image/jpeg"
    if data[:4] == b'\x89PNG':
        ct = "image/png"
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        ct = "image/webp"

    return data, ct
