#!/usr/bin/env python3
"""
Jeju DB Sample (eng) → interactive map

Notion DB를 읽어 Folium 지도(HTML)를 만듭니다.

설치:
  pip install -U notion-client folium requests

실행:
  python n11b_jeju.py

사전 준비:
  1) Notion Integration 생성 후 토큰 복사
  2) 대상 DB → ··· → Connections 에 해당 Integration 연결
  3) 아래 NOTION_TOKEN 에 토큰 붙여넣기

참고 (중요):
  최신 Notion API(2025-09-03) / notion-client 3.x 에서는
  databases.query 가 제거되고 data_sources.query 를 사용합니다.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import folium
import requests
from notion_client import Client

# ============================================================
# 설정 (여기만 수정하면 됩니다)
# ============================================================
NOTION_TOKEN = "xxx"
DATABASE_ID = "yyy"  # Jeju DB Sample (eng)
OUTPUT_HTML = "jeju_map.html"
OUTPUT_JSON = "jeju_spots.json"
# ============================================================

CATEGORY_COLORS = {
    "Eat": "red",
    "Drink": "green",
    "See": "orange",
    "Rest": "purple",
    "Stay": "blue",
}

STATUS_EMOJI = {
    "Visited": "✅",
    "Wishlist": "📌",
}


def clean_id(raw: str) -> str:
    """Notion URL 또는 id 문자열을 UUID 형식으로 정리."""
    raw = raw.strip()
    m = re.search(
        r"([0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        raw,
        re.I,
    )
    if not m:
        raise ValueError(f"Could not parse Notion id from: {raw}")
    value = m.group(1).replace("-", "").lower()
    return f"{value[:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:]}"


def prop_title(prop: dict[str, Any]) -> str:
    parts = prop.get("title") or []
    return "".join(p.get("plain_text", "") for p in parts).strip()


def prop_rich_text(prop: dict[str, Any]) -> str:
    parts = prop.get("rich_text") or []
    return "".join(p.get("plain_text", "") for p in parts).strip()


def prop_select(prop: dict[str, Any]) -> str | None:
    sel = prop.get("select")
    return sel.get("name") if sel else None


def prop_status(prop: dict[str, Any]) -> str | None:
    st = prop.get("status")
    return st.get("name") if st else None


def prop_multi_select(prop: dict[str, Any]) -> list[str]:
    return [x.get("name", "") for x in (prop.get("multi_select") or []) if x.get("name")]


def prop_number(prop: dict[str, Any]) -> float | None:
    return prop.get("number")


def prop_place(prop: dict[str, Any]) -> tuple[float | None, float | None, str | None]:
    """
    Notion Place 속성 best-effort 파싱.
    API 응답 형태가 버전/SDK마다 다를 수 있어 여러 키를 시도합니다.
    """
    if not prop:
        return None, None, None

    # type 필드가 place 인 경우 payload 키가 다를 수 있음
    for key in ("place", "location", prop.get("type")):
        if not key:
            continue
        data = prop.get(key)
        if isinstance(data, dict):
            lat = data.get("lat") or data.get("latitude")
            lon = data.get("lon") or data.get("lng") or data.get("longitude")
            name = data.get("name") or data.get("address")
            if lat is not None and lon is not None:
                return float(lat), float(lon), name

            # nested coordinate object
            coord = data.get("coordinate") or data.get("coordinates") or {}
            if isinstance(coord, dict):
                lat = coord.get("lat") or coord.get("latitude")
                lon = coord.get("lon") or coord.get("lng") or coord.get("longitude")
                if lat is not None and lon is not None:
                    return float(lat), float(lon), name or data.get("name") or data.get("address")

    lat = prop.get("lat") or prop.get("latitude")
    lon = prop.get("lon") or prop.get("lng") or prop.get("longitude")
    if lat is not None and lon is not None:
        return float(lat), float(lon), prop.get("name") or prop.get("address")

    return None, None, None


def geocode_address(address: str, session: requests.Session) -> tuple[float | None, float | None]:
    """Address → 좌표 (OpenStreetMap Nominatim 폴백)."""
    if not address:
        return None, None

    q = address if ("Korea" in address or "Jeju" in address) else f"{address}, Jeju, South Korea"

    resp = session.get(
        "https://nominatim.openstreetmap.org/search",
        params={
            "q": q,
            "format": "json",
            "limit": 1,
            "countrycodes": "kr",
        },
        headers={"User-Agent": "jeju-notion-map-sample/1.0 (local script)"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None, None
    return float(data[0]["lat"]), float(data[0]["lon"])


def resolve_data_source_id(notion: Client, database_id: str) -> str:
    """
    database_id → data_source_id

    최신 API에서는 DB(컨테이너)와 data source(실제 표)가 분리됩니다.
    행 조회는 data_source_id 로 합니다.
    """
    db = notion.databases.retrieve(database_id=database_id)
    sources = db.get("data_sources") or []
    if not sources:
        # 구형 응답 호환: data_sources 가 없으면 database_id 를 그대로 시도
        print("Warning: data_sources not found on database object; falling back to database_id")
        return database_id

    data_source_id = sources[0]["id"]
    name = sources[0].get("name") or "(unnamed)"
    print(f"Resolved data source: {name} ({data_source_id})")
    return data_source_id


def fetch_pages(notion: Client, data_source_id: str) -> list[dict[str, Any]]:
    """data source 페이지 전체 조회 (페이지네이션 포함)."""
    pages: list[dict[str, Any]] = []
    cursor = None

    while True:
        kwargs: dict[str, Any] = {
            "data_source_id": data_source_id,
            "page_size": 100,
        }
        if cursor:
            kwargs["start_cursor"] = cursor

        # 최신 notion-client 3.x
        if hasattr(notion, "data_sources") and hasattr(notion.data_sources, "query"):
            result = notion.data_sources.query(**kwargs)
        else:
            # 구버전 호환 (notion-client 2.x)
            # databases.query 가 있는 경우에만 사용
            if hasattr(notion.databases, "query"):
                # 구 API는 database_id 파라미터 이름 사용
                old_kwargs = {
                    "database_id": data_source_id,
                    "page_size": kwargs["page_size"],
                }
                if cursor:
                    old_kwargs["start_cursor"] = cursor
                result = notion.databases.query(**old_kwargs)
            else:
                # 최후 수단: raw request
                body: dict[str, Any] = {"page_size": 100}
                if cursor:
                    body["start_cursor"] = cursor
                result = notion.request(
                    path=f"data_sources/{data_source_id}/query",
                    method="post",
                    body=body,
                )

        pages.extend(result.get("results", []))
        if not result.get("has_more"):
            break
        cursor = result.get("next_cursor")

    return pages


def page_to_spot(page: dict[str, Any], session: requests.Session) -> dict[str, Any] | None:
    props = page.get("properties", {})

    name = prop_title(props.get("Name", {"title": []}))
    if not name:
        return None

    address = prop_rich_text(props.get("Address", {"rich_text": []}))
    memo = prop_rich_text(props.get("Memo", {"rich_text": []}))
    category = prop_select(props.get("Category", {})) or "Unknown"
    status = prop_status(props.get("Status", {})) or "Unknown"
    rating = prop_select(props.get("⭐ Rating", {})) or ""
    tags = prop_multi_select(props.get("Tag", {}))
    no = prop_number(props.get("No", {}))

    # 1) Position(place) 우선
    lat, lon, place_label = prop_place(props.get("Position", {}))
    source = "place"

    # 2) 없으면 Address 지오코딩
    if lat is None or lon is None:
        source = "geocode"
        lat, lon = geocode_address(address, session)
        time.sleep(1.1)  # Nominatim 예절상 대기

    if lat is None or lon is None:
        print(f"  [skip] no coordinates: {name}")
        return None

    return {
        "name": name,
        "lat": lat,
        "lon": lon,
        "address": address,
        "memo": memo,
        "category": category,
        "status": status,
        "rating": rating,
        "tags": tags,
        "no": no,
        "url": page.get("url"),
        "coord_source": source,
        "place_label": place_label,
    }


def build_map(spots: list[dict[str, Any]]) -> folium.Map:
    if not spots:
        return folium.Map(location=[33.38, 126.55], zoom_start=10)

    avg_lat = sum(s["lat"] for s in spots) / len(spots)
    avg_lon = sum(s["lon"] for s in spots) / len(spots)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=10, tiles="OpenStreetMap")

    groups: dict[str, folium.FeatureGroup] = {}
    for cat in sorted({s["category"] for s in spots}):
        count = sum(1 for s in spots if s["category"] == cat)
        groups[cat] = folium.FeatureGroup(name=f"{cat} ({count})")
        groups[cat].add_to(m)

    for s in spots:
        color = CATEGORY_COLORS.get(s["category"], "gray")
        status_icon = STATUS_EMOJI.get(s["status"], "•")
        tags_html = ", ".join(s["tags"]) if s["tags"] else "-"
        link = (
            f'<a href="{s["url"]}" target="_blank">Open in Notion</a>'
            if s.get("url")
            else ""
        )

        popup_html = f"""
        <div style="min-width:220px;font-family:sans-serif;font-size:13px;">
          <b>{status_icon} {s['name']}</b><br/>
          <span>No: {s['no'] if s['no'] is not None else '-'}</span><br/>
          <span>Category: {s['category']}</span><br/>
          <span>Status: {s['status']}</span><br/>
          <span>Rating: {s['rating'] or '-'}</span><br/>
          <span>Tags: {tags_html}</span><br/>
          <span>Address: {s['address'] or '-'}</span><br/>
          <span>Memo: {s['memo'] or '-'}</span><br/>
          <span style="color:#888">coords via {s['coord_source']}</span><br/>
          {link}
        </div>
        """

        folium.Marker(
            location=[s["lat"], s["lon"]],
            tooltip=f"{s['name']} ({s['category']})",
            popup=folium.Popup(popup_html, max_width=320),
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(groups[s["category"]])

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def main() -> None:
    token = NOTION_TOKEN.strip()
    if not token or token in {"YOUR_TOKEN_HERE", "secret_...", "ntn_..."}:
        raise SystemExit(
            "코드 상단 NOTION_TOKEN 에 Notion Integration 토큰을 넣어주세요.\n"
            '예: NOTION_TOKEN = "ntn_xxxx"'
        )

    database_id = clean_id(DATABASE_ID)
    notion = Client(auth=token)

    print(f"Reading database: {database_id}")
    data_source_id = resolve_data_source_id(notion, database_id)

    pages = fetch_pages(notion, data_source_id)
    print(f"Fetched {len(pages)} pages")

    session = requests.Session()
    spots: list[dict[str, Any]] = []
    for page in pages:
        # page 객체만 지도에 사용
        if page.get("object") not in (None, "page"):
            # data_source 결과가 섞일 수 있어 스킵
            if page.get("object") != "page":
                continue
        spot = page_to_spot(page, session)
        if spot:
            spots.append(spot)
            print(
                f"  + {spot['name']} "
                f"({spot['lat']:.5f}, {spot['lon']:.5f}) "
                f"[{spot['coord_source']}]"
            )

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(spots, f, ensure_ascii=False, indent=2)

    m = build_map(spots)
    m.save(OUTPUT_HTML)

    print(f"\nMap saved → {OUTPUT_HTML}")
    print(f"Spots JSON → {OUTPUT_JSON} ({len(spots)} markers)")
    print("Open the HTML file in a browser.")


if __name__ == "__main__":
    main()
