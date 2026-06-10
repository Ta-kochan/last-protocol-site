"""Regenerate docs/data.js from the YouTube Data API + content/content.json.

- Fetches all uploads from the LAST PROTOCOL channel.
- MVs are videos whose title starts with "[LAST PROTOCOL]".
- LATEST  = the most recently published MV.
- GALLERY = the 3 most-viewed MVs.
- Discography and description copy come from content/content.json (manual).

Usage:
    python scripts/update_content.py

API key resolution: env YOUTUBE_API_KEY, else ../youtube-ads-report/.env.
If no valid key is available, falls back to the channel RSS feed — which only
covers the ~15 most recent uploads, so older MVs are invisible to the
top-by-views ranking until a valid key is configured.
No third-party dependencies (stdlib urllib only).
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANNEL_ID = "UCKlU7YsZ4vhuwDedbdMYYjA"
UPLOADS_PLAYLIST = "UU" + CHANNEL_ID[2:]
MV_PREFIX = "[LAST PROTOCOL]"
API_BASE = "https://www.googleapis.com/youtube/v3"


def resolve_api_key() -> str:
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if key:
        return key
    env_path = ROOT.parent / "youtube-ads-report" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("YOUTUBE_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def api_get(endpoint: str, params: dict) -> dict:
    url = f"{API_BASE}/{endpoint}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def fetch_all_uploads(key: str) -> list[str]:
    ids: list[str] = []
    token = None
    while True:
        params = {
            "part": "contentDetails",
            "playlistId": UPLOADS_PLAYLIST,
            "maxResults": 50,
            "key": key,
        }
        if token:
            params["pageToken"] = token
        data = api_get("playlistItems", params)
        ids += [i["contentDetails"]["videoId"] for i in data.get("items", [])]
        token = data.get("nextPageToken")
        if not token:
            return ids


def fetch_videos(key: str, ids: list[str]) -> list[dict]:
    out: list[dict] = []
    for i in range(0, len(ids), 50):
        data = api_get(
            "videos",
            {
                "part": "snippet,statistics",
                "id": ",".join(ids[i : i + 50]),
                "key": key,
            },
        )
        for item in data.get("items", []):
            out.append(
                {
                    "videoId": item["id"],
                    "title": item["snippet"]["title"],
                    "publishedAt": item["snippet"]["publishedAt"],
                    "views": int(item.get("statistics", {}).get("viewCount", 0)),
                }
            )
    return out


def fetch_videos_rss() -> list[dict]:
    """Fallback: channel RSS feed (only the ~15 most recent uploads)."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        root = ET.fromstring(resp.read())
    ns = {
        "a": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    out: list[dict] = []
    for entry in root.findall("a:entry", ns):
        stats = entry.find("media:group/media:community/media:statistics", ns)
        out.append(
            {
                "videoId": entry.findtext("yt:videoId", "", ns),
                "title": entry.findtext("a:title", "", ns),
                "publishedAt": entry.findtext("a:published", "", ns),
                "views": int(stats.get("views", "0")) if stats is not None else 0,
            }
        )
    return out


def split_title(raw: str, overrides: dict) -> tuple[str, str]:
    """'[LAST PROTOCOL] Sabaku-no-Rondo 錆びた輪舞曲 - Cyberpunk Acoustic Folk'
    -> ('Sabaku-no-Rondo', '錆びた輪舞曲'). The ' - genre' suffix is dropped."""
    if raw in overrides:
        o = overrides[raw]
        return o["titleEn"], o["titleJa"]
    body = raw[len(MV_PREFIX):].strip()
    m = re.search(r"[^\x00-\x7F]", body)  # first non-ASCII char = start of JA part
    if not m:
        return body.split(" - ")[0].strip(), ""
    en, ja = body[: m.start()].strip(), body[m.start():].strip()
    ja = ja.split(" - ")[0].strip()  # drop trailing genre descriptor
    return en, ja


def main() -> None:
    key = resolve_api_key()
    content = json.loads((ROOT / "content" / "content.json").read_text(encoding="utf-8"))

    videos: list[dict] = []
    if key:
        try:
            videos = fetch_videos(key, fetch_all_uploads(key))
        except urllib.error.HTTPError as e:
            print(f"WARN: YouTube Data API failed ({e.code}); falling back to RSS")
    if not videos:
        videos = fetch_videos_rss()
        print(f"WARN: RSS fallback - only the {len(videos)} most recent uploads are "
              "considered. Set a valid YOUTUBE_API_KEY for full coverage.")
    mvs = [v for v in videos if v["title"].upper().startswith(MV_PREFIX)]
    if not mvs:
        sys.exit(f"No videos found with prefix {MV_PREFIX!r}")

    overrides = content.get("title_overrides", {})
    for v in mvs:
        v["titleEn"], v["titleJa"] = split_title(v["title"], overrides)

    latest = max(mvs, key=lambda v: v["publishedAt"])
    top3 = sorted(mvs, key=lambda v: v["views"], reverse=True)[:3]
    latest["desc"] = content.get("latest_desc", {}).get(
        latest["videoId"],
        f"最新作「{latest['titleJa'] or latest['titleEn']}」、全ストリーミングサービスで配信中。",
    )

    data = {
        "latest": {k: latest[k] for k in ("videoId", "titleEn", "titleJa", "desc")},
        "mvs": [{k: v[k] for k in ("videoId", "titleEn", "titleJa", "views")} for v in top3],
        "discography": content["discography"],
    }
    out_path = ROOT / "docs" / "data.js"
    out_path.write_text(
        "// Generated by scripts/update_content.py — do not edit by hand.\n"
        "window.LP_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path}")
    print(f"  LATEST : {latest['titleEn']} ({latest['videoId']})")
    for v in top3:
        print(f"  TOP MV : {v['titleEn']} - {v['views']:,} views ({v['videoId']})")


if __name__ == "__main__":
    main()
