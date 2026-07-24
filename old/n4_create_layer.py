import requests
import folium
from geopy.geocoders import Nominatim

# 설정
TOKEN = "xxx"
DATABASE_ID = "yyy"

# 1. 데이터 가져오기
url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
response = requests.post(url, headers=headers).json()

# 2. 지도 초기화
m = folium.Map(location=[37.7381, 127.0339], zoom_start=13)
geolocator = Nominatim(user_agent="my_restaurant_map_layers")

# 3. 작성자별 그룹 생성
groups = {
    "당근이": folium.FeatureGroup(name="당근이"),
    "휴민트": folium.FeatureGroup(name="휴민트")
}

# 4. 마커 생성 및 그룹 할당
print("지도 레이어 생성 중...")
for page in response.get('results', []):
    props = page['properties']
    name = props['상호명']['title'][0]['plain_text']
    address = props['주소']['rich_text'][0]['plain_text']
    
    # 작성자 확인 (값이 없을 경우 대비)
    author_prop = props.get('작성자', {})
    author = author_prop['select']['name'] if author_prop.get('select') else "기타"
    
    loc = geolocator.geocode(address)
    if loc:
        # 작성자별 마커 색상 구분
        color = 'red' if author == "당근이" else 'blue'
        marker = folium.Marker(
            [loc.latitude, loc.longitude],
            popup=f"{name} ({author})",
            icon=folium.Icon(color=color)
        )
        
        # 해당 작성자 그룹에 추가
        if author in groups:
            marker.add_to(groups[author])
        else:
            marker.add_to(m) # 그룹이 없으면 기본 지도에 표시

# 5. 그룹과 레이어 컨트롤 추가
for group in groups.values():
    group.add_to(m)
folium.LayerControl().add_to(m)

m.save("map_with_layers.html")
print("완료! 'map_with_layers.html' 파일을 열어보세요.")