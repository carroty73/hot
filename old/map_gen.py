# n10_category_9.py와 동일한 파일임
# 위 파일 이름이 너무 길잖아.

# sudo systemctl status hot_web # 현재 상태 보기
# sudo systemctl stop hot_web # 현재 상태 보기
# sudo systemctl start hot_web # # 서비스 시작하기
# python3 map_gen.py # 지도 생성
# sudo systemctl restart hot_web # 서비스 재시작

# 노션이 레코드드 정보를 1번에 100개 밖에 안주니, 100개가 넘어가면 100 개 이상을 못읽어옴
# 그래서 100개 읽고, 또 있니? yes 또 읽기 이런식으로 고쳐야 함
import requests
import folium
import json
import re

# 설정
KAKAO_API_KEY = "xxx"
NOTION_TOKEN = "yyy"
NOTION_DB_ID = "zzz"

"""
CARROT_ICON_IMAGE = "./rsc/img/carrot.png"
HUMINT_ICON_IMAGE = "./rsc/icons/pack_2/humint.png"

HOUSE_ICON_IMAGE = "./rsc/icons/pack_2/house.png"
HERI_ICON_IMAGE = "./rsc/icons/pack_2/heri.png"
REST_ICON_IMAGE = "./rsc/icons/pack_2/rest.png"
"""

ICON_DIR = "./rsc/icons/pack_2"

SEE_ICON_IMAGE = f"{ICON_DIR}/01_see.png"
LEARN_ICON_IMAGE = f"{ICON_DIR}/02_learn.png"
DRINK_ICON_IMAGE = f"{ICON_DIR}/03_drink.png"
EAT_ICON_IMAGE = f"{ICON_DIR}/04_eat.png"
PLAY_ICON_IMAGE = f"{ICON_DIR}/05_play.png"
REST_ICON_IMAGE = f"{ICON_DIR}/06_rest.png"
STAY_ICON_IMAGE = f"{ICON_DIR}/07_stay.png"
MOVE_ICON_IMAGE = f"{ICON_DIR}/08_move.png"
OTHER_ICON_IMAGE = f"{ICON_DIR}/09_other.png"

def fetch_all_pages(db_id, headers):
    """Notion DB를 100개씩 이어서 전부 가져온다."""
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    all_results = []
    payload = {"page_size": 100}
    page_num = 1

    while True:
        res = requests.post(url, headers=headers, json=payload).json()

        # Notion API 에러 응답 방어
        if "results" not in res:
            print(f"Notion 응답 오류: {res}")
            break

        batch = res.get("results", [])
        all_results.extend(batch)
        print(f"{page_num}회차: {len(batch)}개 수신 (누적 {len(all_results)}개)")

        if not res.get("has_more"):
            break

        payload["start_cursor"] = res["next_cursor"]
        page_num += 1

    return all_results

def get_kakao_coords(address, api_key):
    # API 요청을 위한 헤더 설정 (KakaoAK 접두어 필수)
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": address.strip()}



    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        data = response.json()
        
        if data.get('documents') and len(data['documents']) > 0:
            item = data['documents'][0]
            return float(item['y']), float(item['x']) # 위도, 경도
        return None, None
    except Exception as e:
        print(f"API 호출 오류: {e}")
        return None, None





# 1. 노션 데이터 가져오기
#url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
#headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
#response = requests.post(url, headers=headers).json() # 1번만 읽지 말고, 여러번 읽자.

# 1. 노션 데이터 가져오기 (100개 초과도 전부)
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
pages = fetch_all_pages(NOTION_DB_ID, headers)
print(f"총 {len(pages)}개 페이지 로드 완료")

# 지도 시작 위치/축적
MAP_LAT = 37.738060   # 위도
MAP_LON = 127.046110  # 경도
MAP_ZOOM = 13         # 축적 (클수록 확대)

# 2. 지도 초기화
m = folium.Map(location=[MAP_LAT, MAP_LON], zoom_start=MAP_ZOOM, tiles=None)


folium.TileLayer("CartoDB positron", name="밝은 지도").add_to(m)
folium.TileLayer("CartoDB dark_matter", name="어두운 지도").add_to(m)
folium.TileLayer("OpenStreetMap", name="기본 지도").add_to(m)


# 3. 타이틀 및 방문자 수 코드 추가
# 3. 타이틀 및 방문자 수 (반응형)
title_html = '''
<style>
  /* 제목 카드 */
  .hot-title {
    position: fixed;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    width: min(92vw, 300px);
    max-width: calc(100vw - 24px);
    box-sizing: border-box;
    padding: 10px 14px;
    text-align: center;
    color: #111;
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 14px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.35;
    pointer-events: none; /* 카드 아래 지도 드래그 방해 줄임 */
  }
  .hot-title__name {
    display: block;
    font-size: clamp(16px, 4.2vw, 22px);
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .hot-title__visit {
    display: block;
    margin-top: 4px;
    font-size: clamp(12px, 3.2vw, 14px);
    font-weight: 500;
    color: #444;
  }

  /* 왼쪽 줌 버튼과 겹침 방지 (넓은 화면) */
  @media (min-width: 640px) {
    .hot-title {
      left: 56px;
      transform: none;
      width: min(90vw, 280px);
    }
  }

  /* 아주 좁은 화면 */
  @media (max-width: 380px) {
    .hot-title {
      top: 8px;
      padding: 8px 10px;
      border-radius: 12px;
    }
  }

  /* 팝업 반응형 */
  .hot-popup {
    width: min(70vw, 180px);
    max-width: 200px;
    text-align: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.4;
  }
  .hot-popup__name {
    margin: 0 0 6px;
    font-size: 15px;
    font-weight: 700;
    color: #111;
    word-break: keep-all;
  }
  .hot-popup__cat {
    margin: 0 0 10px;
    font-size: 13px;
    color: #555;
  }
  .hot-popup__link {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: #fff4e8;
    color: #e67e00;
    font-size: 13px;
    font-weight: 700;
    text-decoration: none;
  }

  /* Leaflet 팝업이 화면 밖으로 과도하게 커지지 않게 */
  .leaflet-popup-content {
    margin: 10px 12px !important;
  }
  .leaflet-popup-content-wrapper {
    border-radius: 12px !important;
  }
</style>

<div class="hot-title">
  <span class="hot-title__name">당근이의 의정부 핫플</span>
  <span class="hot-title__visit">
    방문자 수: <span id="visit-count">로딩중...</span>
  </span>
</div>

<script>
  fetch('/count.txt?' + Math.random())
    .then(r => r.text())
    .then(t => {
      const el = document.getElementById('visit-count');
      if (el) el.innerText = t.trim();
    })
    .catch(() => {
      const el = document.getElementById('visit-count');
      if (el) el.innerText = '-';
    });
</script>
'''
m.get_root().html.add_child(folium.Element(title_html))

# 4. 작성자별 그룹 생성

groups = {
    "볼 거리": folium.FeatureGroup(name="볼 거리"),
    "알아갈 거리": folium.FeatureGroup(name="알아갈 거리"),
    "마실 거리": folium.FeatureGroup(name="마실 거리"),
    "먹을 거리": folium.FeatureGroup(name="먹을 거리"),
    "즐길 거리": folium.FeatureGroup(name="즐길 거리"),
    "쉴 거리": folium.FeatureGroup(name="쉴 거리"),
    "숙소": folium.FeatureGroup(name="숙소"),
    "교통": folium.FeatureGroup(name="교통"),
    "기타": folium.FeatureGroup(name="기타"),
}


"""
1. 볼 거리 (See)
2. 알아갈 거리 (Learn)
3. 마실 거리 (Drink)
4. 먹을 거리 (Eat)
5. 즐길 거리 (Play)
6. 쉴 거리 (Rest)
7. 숙소 (Stay)
8. 교통 (Move)
9. 기타 (Other)

Tally Select에 올릴것, 글자 하나 틀리면 안댐
볼 거리
알아갈 거리
마실 거리
먹을 거리
즐길 거리
쉴 거리
숙소
교통
기타
"""


# 5. 데이터 파싱 및 마커 추가
print("지도 생성 시작...")
# 아이콘 설정
"""
if category == "집":
    icon = folium.CustomIcon(HOUSE_ICON_IMAGE, icon_size=(30, 30))
elif category == "식당":
    icon = folium.CustomIcon(REST_ICON_IMAGE, icon_size=(30, 30))
elif category == "유적":
    icon = folium.CustomIcon(HERI_ICON_IMAGE, icon_size=(30, 30))            
else:
    icon = folium.Icon(color='gray', icon='info-sign')            
"""

# if-else가 지저분하니, switch-case를 쓰면 좋겠지만,
# 딕셔너리도 괜찮네 머
# # 먼저 아이콘 설정 정보를 딕셔너리로 미리 정의합니다 (루프 밖 상단에 두면 더 좋아요)
# icon_map = {
#     "집": folium.CustomIcon(HOUSE_ICON_IMAGE, icon_size=(30, 30)),
#     "식당": folium.CustomIcon(REST_ICON_IMAGE, icon_size=(30, 30)),
#     "유적": folium.CustomIcon(HERI_ICON_IMAGE, icon_size=(30, 30)),
# }


icon_map = {
    "볼 거리": folium.CustomIcon(SEE_ICON_IMAGE, icon_size=(30, 30)),
    "알아갈 거리": folium.CustomIcon(LEARN_ICON_IMAGE, icon_size=(30, 30)),
    "마실 거리": folium.CustomIcon(DRINK_ICON_IMAGE, icon_size=(30, 30)),
    "먹을 거리": folium.CustomIcon(EAT_ICON_IMAGE, icon_size=(30, 30)),
    "즐길 거리": folium.CustomIcon(PLAY_ICON_IMAGE, icon_size=(30, 30)),
    "쉴 거리": folium.CustomIcon(REST_ICON_IMAGE, icon_size=(30, 30)),
    "숙소": folium.CustomIcon(STAY_ICON_IMAGE, icon_size=(30, 30)),
    "교통": folium.CustomIcon(MOVE_ICON_IMAGE, icon_size=(30, 30)),
    "기타": folium.CustomIcon(OTHER_ICON_IMAGE, icon_size=(30, 30)),
}



#for page in response.get('results', []):
for page in pages:    # 100개 넘어 읽어오기로 바꿈
    try:
        if not isinstance(page, dict):
            print(f"이상한 데이터 발견 (type: {type(page)}): {page}")
            continue

        # properties가 없는 경우를 대비
        if 'properties' not in page:
            print(f"properties 키가 없는 페이지 발견: {page.get('id', 'ID없음')}")
            continue
        
        props = page.get('properties', {})
        #page_url = page.get('url', '#')        
        props = page['properties']

        #print(f"DEBUG: 페이지 정보 확인 -> {page.get('url')}")
        page_url = page.get('url', '#')

        
        # 1. 이름 체크: title 리스트가 비어있는지 확인
        if not props.get('이름', {}).get('title'):
            print("데이터 누락: 이름 없음, 건너뜁니다.")
            continue
        name = props['이름']['title'][0]['plain_text']

        # 2. 주소 체크: rich_text 리스트가 비어있는지 확인
        if not props.get('주소', {}).get('rich_text'):
            print(f"데이터 누락: {name} - 주소 없음, 건너뜁니다.")
            continue
        raw_address = props['주소']['rich_text'][0]['plain_text']
        
        # 3. 카테고리 체크: select 속성이 None일 수도 있음
        category_data = props.get('카테고리', {})
        category = category_data.get('select', {}).get('name', '기타') if category_data else '기타'

        # 주소 정제 (이름 및 괄호 제거 후 주소만 추출)
        #match = re.search(r'(경기[도]?[\s\w\d\-]+)', raw_address)
        #clean_addr = match.group(1).strip() if match else raw_address
        clean_addr = raw_address.strip()
        
        lat, lon = get_kakao_coords(clean_addr, KAKAO_API_KEY)

        icon = icon_map.get(category, folium.Icon(color='gray', icon='info-sign'))            


        # # 루프 안에서는 이렇게 한 줄로 끝냅니다!
        # # .get(category, 기본값)을 사용해서 매칭되는 게 없으면 회색 아이콘을 줍니다.
        # icon = icon_map.get(category, folium.Icon(color='gray', icon='info-sign'))   

        
        if not lat or not lon:
            print(f"검색 실패: {name} (주소: {clean_addr})")
            continue
         


        popup_content = f"""
        <div style="width: 150px; text-align: center;">
            <p><b>{name}</b></p>
            <p>분류: {category}</p>
            <a href="{page_url}" target="_blank" style="text-decoration:none; color:orange; font-weight:bold;">
                📍 노션에서 확인하기
            </a>
        </div>
        """

        #old marker = folium.Marker([lat, lon], popup=f"{name} ({category})", icon=icon)
        marker = folium.Marker(
            [lat, lon], 
            popup=folium.Popup(popup_content, max_width=200), 
            icon=icon
        )
        
        if category in groups:
            marker.add_to(groups[category])
        else:
            marker.add_to(m)
    except Exception as e:
        print(f"데이터 파싱 오류: {e.__class__.__name__} - {e}")
        continue

# 6. 그룹 등록 및 경계선
for group in groups.values():
    group.add_to(m)

with open('uijeongbu_dong.geojson', 'r', encoding='utf-8') as f:
    uijeongbu_geo = json.load(f)

folium.GeoJson(
    uijeongbu_geo,
    name="의정부 경계선",
    style_function=lambda x: {'fillColor': 'blue', 'color': 'black', 'weight': 2, 'fillOpacity': 0.1}
).add_to(m) 


folium.LayerControl(collapsed=True).add_to(m)

m.save("index.html")
print("완료! 'index.html'을 확인하세요.")