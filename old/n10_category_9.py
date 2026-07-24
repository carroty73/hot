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
HUMINT_ICON_IMAGE = "./rsc/img/humint.png"

HOUSE_ICON_IMAGE = "./rsc/img/house.png"
HERI_ICON_IMAGE = "./rsc/img/heri.png"
REST_ICON_IMAGE = "./rsc/img/rest.png"
"""

SEE_ICON_IMAGE = "./rsc/img/01_see.png"
LEARN_ICON_IMAGE = "./rsc/img/02_learn.png"
DRINK_ICON_IMAGE = "./rsc/img/03_drink.png"
EAT_ICON_IMAGE = "./rsc/img/04_eat.png"
PLAY_ICON_IMAGE = "./rsc/img/05_play.png"
REST_ICON_IMAGE = "./rsc/img/06_rest.png"
STAY_ICON_IMAGE = "./rsc/img/07_stay.png"
MOVE_ICON_IMAGE = "./rsc/img/08_move.png"
OTHER_ICON_IMAGE = "./rsc/img/09_other.png"

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
url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
response = requests.post(url, headers=headers).json()

# 2. 지도 초기화
m = folium.Map(location=[37.738060, 127.046110], zoom_start=15, tiles=None)
folium.TileLayer("CartoDB positron", name="밝은 지도").add_to(m)
folium.TileLayer("CartoDB dark_matter", name="어두운 지도").add_to(m)
folium.TileLayer("OpenStreetMap", name="기본 지도").add_to(m)

# 3. 타이틀 및 방문자 수 코드 추가
title_html = '''
<div style="position: fixed; top: 10px; left: 50px; width: 250px; height: 75px; 
            z-index:9999; font-size:24px; font-weight:bold; color:black; 
            background-color:rgba(255,255,255,0.7); padding: 10px; 
            border-radius: 10px; border: 2px solid #ccc; text-align: center;">
    당근이의 의정부 핫플
    <br><span style="font-size:14px;">방문자 수: <span id="visit-count">로딩중...</span></span>
</div>
<script>
    fetch('/count.txt?' + Math.random())
    .then(r => r.text())
    .then(t => document.getElementById('visit-count').innerText = t);
</script>
'''
m.get_root().html.add_child(folium.Element(title_html))

# 4. 작성자별 그룹 생성

# groups = {
#     "집": folium.FeatureGroup(name="집"),
#     "식당": folium.FeatureGroup(name="식당"),
#     "유적": folium.FeatureGroup(name="유적"),
# }

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
for page in response.get('results', []):
    try:
    # [디버깅 추가] page가 아예 None이거나 dict가 아닐 경우 대비
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
        
        if not lat or not lon:
            print(f"검색 실패: {name} (주소: {clean_addr})")
            continue

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

        icon = icon_map.get(category, folium.Icon(color='gray', icon='info-sign'))            


        # if-else가 지저분하니, switch-case를 쓰면 좋겠지만,
        # 딕셔너리도 괜찮네 머
        # # 먼저 아이콘 설정 정보를 딕셔너리로 미리 정의합니다 (루프 밖 상단에 두면 더 좋아요)
        # icon_map = {
        #     "집": folium.CustomIcon(HOUSE_ICON_IMAGE, icon_size=(30, 30)),
        #     "식당": folium.CustomIcon(REST_ICON_IMAGE, icon_size=(30, 30)),
        #     "유적": folium.CustomIcon(HERI_ICON_IMAGE, icon_size=(30, 30)),
        # }

        # # 루프 안에서는 이렇게 한 줄로 끝냅니다!
        # # .get(category, 기본값)을 사용해서 매칭되는 게 없으면 회색 아이콘을 줍니다.
        # icon = icon_map.get(category, folium.Icon(color='gray', icon='info-sign'))            


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

folium.LayerControl(collapsed=False).add_to(m)

m.save("index.html")
print("완료! 'index.html'을 확인하세요.")