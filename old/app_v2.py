from flask import Flask, send_file, send_from_directory, request, render_template, jsonify
import os
import requests

app = Flask(__name__)

COUNT_FILE = "count.txt"
MY_IP = "221.138.105.134"

KAKAO_API_KEY = "d274d5ddb20b3154cc543820582e82a1"
NOTION_TOKEN = "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"
NOTION_DB_ID = "9db00fa7a2e744aaaa2373a2c62c599b"

MAP_LAT = 37.738060
MAP_LON = 127.046110
MAP_ZOOM = 13

CATEGORY_VISIBLE = {
    "볼 거리": True,
    "알아갈 거리": True,
    "마실 거리": True,
    "먹을 거리": True,
    "즐길 거리": True,
    "쉴 거리": True,
    "숙소": True,
    "교통": True,
    "기타": True,
}

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def fetch_all_pages(db_id):
    url = "https://" + "api.notion.com/v1/databases/" + db_id + "/query"
    results = []
    payload = {"page_size": 100}

    while True:
        res = requests.post(url, headers=NOTION_HEADERS, json=payload, timeout=30).json()
        if "results" not in res:
            raise RuntimeError(f"Notion 응답 오류: {res}")
        results.extend(res["results"])
        if not res.get("has_more"):
            break
        payload["start_cursor"] = res["next_cursor"]
    return results


def get_kakao_coords(address):
    url = "https://" + "dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        data = requests.get(
            url,
            headers=headers,
            params={"query": address.strip()},
            timeout=5,
        ).json()
        docs = data.get("documents") or []
        if not docs:
            return None, None
        return float(docs[0]["y"]), float(docs[0]["x"])
    except Exception as e:
        print(f"카카오 오류: {e}")
        return None, None


def plain_title(prop):
    arr = (prop or {}).get("title") or []
    return arr[0]["plain_text"] if arr else ""


def plain_text(prop):
    arr = (prop or {}).get("rich_text") or []
    return arr[0]["plain_text"] if arr else ""


def select_name(prop, default="기타"):
    sel = (prop or {}).get("select")
    if not sel:
        return default
    return sel.get("name") or default


def number_or_none(prop):
    if not prop:
        return None
    return prop.get("number")


@app.route("/")
def index():
    return render_template("intro.html")


@app.route("/hot/")
def hot():
    return send_file("hot.html")


@app.route("/uijeongbu_dong.geojson")
def uijeongbu_geojson():
    """의정부 경계선 GeoJSON"""
    return send_file("uijeongbu_dong.geojson")


@app.route("/api/places")
def api_places():
    try:
        pages = fetch_all_pages(NOTION_DB_ID)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    places = []
    for page in pages:
        props = page.get("properties") or {}

        name = plain_title(props.get("이름"))
        address = plain_text(props.get("주소"))
        if not name or not address:
            continue

        category = select_name(props.get("카테고리"), "기타")

        lat = number_or_none(props.get("위도"))
        lon = number_or_none(props.get("경도"))
        if lat is None or lon is None:
            lat, lon = get_kakao_coords(address)

        if not lat or not lon:
            print(f"좌표 실패: {name} / {address}")
            continue

        places.append({
            "name": name,
            "address": address,
            "category": category,
            "lat": lat,
            "lon": lon,
            "url": page.get("url", "#"),
        })

    return jsonify({
        "map": {
            "lat": MAP_LAT,
            "lon": MAP_LON,
            "zoom": MAP_ZOOM,
        },
        "categoryVisible": CATEGORY_VISIBLE,
        "places": places,
        "count": len(places),
    })


@app.route("/rsc/<path:filename>")
def rsc_files(filename):
    return send_from_directory("rsc", filename)


@app.route("/count.txt")
def get_count():
    if request.remote_addr != MY_IP:
        if not os.path.exists(COUNT_FILE):
            count = 1
        else:
            with open(COUNT_FILE, "r") as f:
                count = int(f.read()) + 1
        with open(COUNT_FILE, "w") as f:
            f.write(str(count))
    else:
        count = open(COUNT_FILE).read() if os.path.exists(COUNT_FILE) else 0
    return str(count)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
