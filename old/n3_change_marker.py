import requests
import folium
from geopy.geocoders import Nominatim

# 설정
TOKEN = "xxx"
DATABASE_ID = "yyy"

# 1. 노션에서 데이터 가져오기
url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
response = requests.post(url, headers=headers).json()

# 2. 지도 생성 (의정부 중심)
m = folium.Map(location=[37.7381, 127.0339], zoom_start=13)
geolocator = Nominatim(user_agent="my_restaurant_map_custom")

# 3. 데이터 파싱 및 커스텀 마커 추가
print("마커를 변경하여 지도 생성 중...")
for page in response.get('results', []):
    props = page['properties']
    name = props['상호명']['title'][0]['plain_text']
    address = props['주소']['rich_text'][0]['plain_text']
    
    # 당슐랭 정보 가져오기 (만약 없다면 기본값 0)
    rating_prop = props.get('당슐랭', {})
    rating = rating_prop.get('number', 0) if rating_prop else 0

    # 주소를 좌표로 변환 (지오코딩)
    loc = geolocator.geocode(address)
    if loc:
        # 4. 당슐랭에 따른 마커 색상 & 아이콘 설정
        if rating >= 4:
            icon_color = 'red'
            icon_name = 'heart' # 하트 아이콘
        else:
            icon_color = 'blue'
            icon_name = 'cutlery' # 숟가락/포크 아이콘
        
        # 커스텀 마커 추가
        folium.Marker(
            [loc.latitude, loc.longitude],
            popup=name,
            icon=folium.Icon(color=icon_color, icon=icon_name, prefix='fa') # fa는 font-awesome 사용 시 필수
        ).add_to(m)
        print(f"추가 완료: {name} (별점: {rating})")

m.save("map_custom.html")
print("완료! 'map_custom.html' 파일을 열어보세요.")