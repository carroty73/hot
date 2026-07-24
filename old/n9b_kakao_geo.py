import requests
import folium
import json
import re

# 설정
KAKAO_API_KEY = "xxx"
TOKEN = "yyy"
DATABASE_ID = "zzz"

CARROT_ICON_IMAGE = "carrot.png"
HUMINT_ICON_IMAGE = "humint.png"

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
url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
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
    당근이의 의정부 맛집
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
groups = {
    "당근이": folium.FeatureGroup(name="당근이"),
    "휴민트": folium.FeatureGroup(name="휴민트")
}

# 5. 데이터 파싱 및 마커 추가
print("지도 생성 시작...")
for page in response.get('results', []):
    try:
        props = page['properties']
        
        # 1. 상호명 체크: title 리스트가 비어있는지 확인
        if not props.get('상호명', {}).get('title'):
            print("데이터 누락: 상호명 없음, 건너뜁니다.")
            continue
        name = props['상호명']['title'][0]['plain_text']

        # 2. 주소 체크: rich_text 리스트가 비어있는지 확인
        if not props.get('주소', {}).get('rich_text'):
            print(f"데이터 누락: {name} - 주소 없음, 건너뜁니다.")
            continue
        raw_address = props['주소']['rich_text'][0]['plain_text']
        
        # 3. 작성자 체크: select 속성이 None일 수도 있음
        author_data = props.get('작성자', {})
        author = author_data.get('select', {}).get('name', '기타') if author_data else '기타'

        # 주소 정제 (상호명 및 괄호 제거 후 주소만 추출)
        match = re.search(r'(경기[도]?[\s\w\d\-]+)', raw_address)
        clean_addr = match.group(1).strip() if match else raw_address
        
        lat, lon = get_kakao_coords(clean_addr, KAKAO_API_KEY)
        
        if not lat or not lon:
            print(f"검색 실패: {name} (주소: {clean_addr})")
            continue

        # 아이콘 설정
        if author == "당근이":
            icon = folium.CustomIcon(CARROT_ICON_IMAGE, icon_size=(30, 30))
        elif author == "휴민트":
            icon = folium.CustomIcon(HUMINT_ICON_IMAGE, icon_size=(30, 30))
        else:
            icon = folium.Icon(color='gray', icon='info-sign')
            
        marker = folium.Marker([lat, lon], popup=f"{name} ({author})", icon=icon)
        
        if author in groups:
            marker.add_to(groups[author])
        else:
            marker.add_to(m)

    except Exception as e:
        print(f"데이터 파싱 오류: {e}")
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