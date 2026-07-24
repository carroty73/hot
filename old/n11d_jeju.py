#!/usr/bin/env python3
"""
Jeju DB Sample (eng) → interactive map

Notion DB를 읽어 Folium 지도(HTML)를 만듭니다.
지도 배경은 Layer Control 에서 English / Korean 전환 가능합니다.

설치:
  pip install -U notion-client folium requests

실행:
  python n11b_jeju.py

사전 준비:
  1) Notion Integration 생성 후 토큰 복사
  2) 대상 DB → ··· → Connections 에 해당 Integration 연결
  3) 아래 NOTION_TOKEN 에 토큰 붙여넣기

참고:
  최신 Notion API / notion-client 3.x 에서는
  databases.query 대신 data_sources.query 를 사용합니다.

    1. 토큰은 별도 변수로
        Streamlit에는 Secrets 설정 기능이 있습니다. 나중에 app.py를 다 올리고 나면, Streamlit Cloud의 설정 메뉴에서 Secrets라는 곳에 안전하게 토큰을 저장할 수 있습니다.
        db 아이디는 노출되도 별 상관없다. Integration Token(NOTION_TOKEN)이 없기 때문에 
    2. import os
        까먹지 말자
    3. 코드 수정
    #m.save(OUTPUT_HTML)
    
    m = build_map(spots)
    st_folium(m, width=700, height=500)  

    4. 노션에서 여백을 못 쫓아올때
    지도가 전체 너비를 꽉 채우도록 설정을 바꾸기
    st_folium(m, width=None, height=500)
    width=None으로 설정하면 스트림릿이 부모 컨테이너(여기서는 노션의 임베드 창)의 크기에 맞춰 자동으로 너비를 조절하려고 시도

    5. 스트림릿의 기본 여백 제거
    st.set_page_config(layout="wide") # 페이지 전체를 넓게 사용하도록 설정

"""

from __future__ import annotations

import os
import json
import re
import time
from typing import Any

import folium
import requests
from notion_client import Client

import streamlit as st
from streamlit_folium import st_folium # 설치: pip install streamlit-folium

st.set_page_config(layout="wide") # streamlit 페이지 전체를 넓게 사용하도록 설정
# ============================================================
# 설정 (여기만 수정하면 됩니다)
# ============================================================
#NOTION_TOKEN = "ntn_12345678" # 여기에 토큰을 적지 마세요. 로컬로 테스트하면 몰라도 이상태로 github에 올리는건 위험해요.
#NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_TOKEN = st.secrets["NOTION_TOKEN"] # streamlit secrets 에서 가져오기
DATABASE_ID = "39ff99a4-bb23-801f-9e18-fa4748aedacb"  # Jeju DB Sample (eng)
OUTPUT_HTML = "jeju_map.html"
OUTPUT_JSON = "jeju_spots.json"

# 기본으로 켤 베이스맵: "en" 또는 "ko"
DEFAULT_BASEMAP = "en"
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

            coord = data.get("coordinate") or data.get("coordinates") or {}
            if isinstance(coord, dict):
                lat = coord.get("lat") or coord.get("latitude")
                lon = coord.get("lon") or coord.get("lng") or coord.get("longitude")
                if lat is not None and lon is not None:
                    return (
                        float(lat),
                        float(lon),
                        name or data.get("name") or data.get("address"),
                    )

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
            if hasattr(notion.databases, "query"):
                old_kwargs = {
                    "database_id": data_source_id,
                    "page_size": kwargs["page_size"],
                }
                if cursor:
                    old_kwargs["start_cursor"] = cursor
                result = notion.databases.query(**old_kwargs)
            else:
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


def build_map(spots: list[dict[str, Any]], default_basemap: str = "en") -> folium.Map:
    """
    지도 생성.

    Layer Control 에서:
      - English basemap (Esri World Street Map)
      - Korean basemap (OpenStreetMap, 로컬 지명)
    을 라디오 버튼처럼 전환할 수 있습니다.
    """
    if spots:
        avg_lat = sum(s["lat"] for s in spots) / len(spots)
        avg_lon = sum(s["lon"] for s in spots) / len(spots)
    else:
        avg_lat, avg_lon = 33.38, 126.55

    # tiles=None 으로 시작 → 아래 TileLayer 로 직접 추가
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=10, tiles=None)

    show_en = default_basemap.lower() != "ko"
    show_ko = not show_en

    # English-leaning basemap
    folium.TileLayer(
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
        ),
        attr=(
            "Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, "
            "USGS, Intermap, iPC, NRCAN, Esri Japan, METI, "
            "Esri China (Hong Kong), Esri (Thailand), TomTom"
        ),
        name="English basemap",
        overlay=False,   # base layer → 라디오 전환
        control=True,
        show=show_en,
        max_zoom=19,
    ).add_to(m)

    # Korean / local-name basemap
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Korean basemap",
        overlay=False,   # base layer → 라디오 전환
        control=True,
        show=show_ko,
        max_zoom=19,
    ).add_to(m)

    # Category marker layers (checkbox style overlays)
    groups: dict[str, folium.FeatureGroup] = {}
    for cat in sorted({s["category"] for s in spots}):
        count = sum(1 for s in spots if s["category"] == cat)
        groups[cat] = folium.FeatureGroup(name=f"{cat} ({count})", show=True)
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

        target = groups.get(s["category"], m)
        folium.Marker(
            location=[s["lat"], s["lon"]],
            tooltip=f"{s['name']} ({s['category']})",
            popup=folium.Popup(popup_html, max_width=320),
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(target)

    # 우상단 레이어 컨트롤
    # - English basemap / Korean basemap : 라디오(하나만 선택)
    # - Eat/Drink/See/... : 체크박스(여러 개 가능)
    folium.LayerControl(collapsed=False, position="topright").add_to(m)
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
        if page.get("object") not in (None, "page"):
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

    m = build_map(spots, default_basemap=DEFAULT_BASEMAP)
    #m.save(OUTPUT_HTML)
    
    m = build_map(spots)
    #st_folium(m, width=700, height=500)
    st_folium(m, width=None, height=500) # 노션을 가로 길이를 따라가도록 설정

    print(f"\nMap saved → {OUTPUT_HTML}")
    print(f"Spots JSON → {OUTPUT_JSON} ({len(spots)} markers)")
    print("Open the HTML file in a browser.")
    print("Use the top-right Layer Control to switch English / Korean basemap.")


if __name__ == "__main__":
    main()
