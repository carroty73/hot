import requests
import folium
from geopy.geocoders import Nominatim
import json
import time

# 설정
TOKEN = "xxx"
DATABASE_ID = "yyy"

CARROT_ICON_IMAGE = "carrot.png"
HUMINT_ICON_IMAGE = "humint.png"

url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
response = requests.post(url, headers=headers).json()

# 1. 지도 초기화
m = folium.Map(location=[37.738060, 127.046110], zoom_start=15, tiles=None)

# 2. 타일 추가 (LayerControl에 자동으로 포함됨)
#folium.TileLayer("CartoDB positron", name="Positron").add_to(m)
#folium.TileLayer("CartoDB dark_matter", name="Dark Matter").add_to(m)
#folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)

folium.TileLayer("CartoDB positron", name="밝은 지도 (Positron)").add_to(m)
folium.TileLayer("CartoDB dark_matter", name="어두운 지도 (Dark)").add_to(m)
folium.TileLayer("OpenStreetMap", name="기본 지도 (OSM)").add_to(m)

# 3. 타이틀 추가
title_html = '''
<div style="position: fixed; top: 10px; left: 50px; width: 250px; height: 75px; 
            z-index:9999; font-size:24px; font-weight:bold; color:black; 
            background-color:rgba(255,255,255,0.7); padding: 10px; 
            border-radius: 10px; border: 2px solid #ccc; text-align: center;">
    당근이의 의정부 맛집
    <br><span style="font-size:14px;">방문자 수: <span id="visit-count">로딩중...</span></span>
</div>
<script>
    // 페이지 접속 시 서버의 count.txt를 읽어옴
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

geolocator = Nominatim(user_agent="my_restaurant_map_image_custom")
MARKER_WIDTH, MARKER_HEIGHT = 30, 30

# 5. 데이터 파싱 및 마커 추가
print("이미지 마커를 사용하여 지도 생성 중...")
for page in response.get('results', []):
    try:
        props = page['properties']
        # 필수 정보 추출 (이 부분에서 Key Error가 자주 발생할 수 있음)
        name = props['상호명']['title'][0]['plain_text']
        address = props['주소']['rich_text'][0]['plain_text']
        
        # 주소 정제
        #clean_addr = address.split(' 106')[0] 
        clean_addr = address
        
        author_prop = props.get('작성자', {})
        author = author_prop['select']['name'] if author_prop.get('select') else "기타"
        
        loc = geolocator.geocode(clean_addr)
        
        if not loc:
            print(f"[주소 오류] 지오코딩 실패: {name} (주소: {clean_addr})")
            continue # 다음 맛집으로 건너뜀

        # 마커 아이콘 설정
        if author == "당근이":
            icon = folium.CustomIcon(CARROT_ICON_IMAGE, icon_size=(MARKER_WIDTH, MARKER_HEIGHT))
        elif author == "휴민트":
            icon = folium.CustomIcon(HUMINT_ICON_IMAGE, icon_size=(MARKER_WIDTH, MARKER_HEIGHT))
        else:
            icon = folium.Icon(color='gray', icon='info-sign')
            
        marker = folium.Marker([loc.latitude, loc.longitude], popup=f"{name} ({author})", icon=icon)
        
        if author in groups:
            marker.add_to(groups[author])
        else:
            marker.add_to(m)

    except (KeyError, IndexError) as e:
        # 노션 DB 속성이 비어있거나 형식이 다를 때 에러 출력
        print(f"[데이터 오류] 파싱 실패: {page.get('id')} - 원인: {e}")
        continue
    except Exception as e:
        # 예상치 못한 기타 에러
        print(f"[기타 오류] 알 수 없는 오류 발생: {e}")
        continue

# 6. 그룹을 지도에 등록
for group in groups.values():
    group.add_to(m)

# 경계 데이터 로드
with open('uijeongbu_dong.geojson', 'r', encoding='utf-8') as f:
    uijeongbu_geo = json.load(f)

# GeoJson 레이어 생성 및 지도에 추가
folium.GeoJson(
    uijeongbu_geo,
    name="의정부 경계선",
    style_function=lambda x: {
        'fillColor': 'blue',    # 내부 색상
        'color': 'black',      # 선 색상
        'weight': 2,           # 선 두께
        'fillOpacity': 0.1     # 투명도
    }
).add_to(m)    

# 7. 레이어 컨트롤은 딱 한 번만 추가 (가장 중요)
folium.LayerControl(collapsed=False).add_to(m)

m.save("index.html")
print("완료! 'index.html' 파일을 확인하세요.")