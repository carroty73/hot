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
geolocator = Nominatim(user_agent="my_restaurant_map")

# 3. 데이터 파싱 및 마커 추가
print("지도 생성 중...")
for page in response.get('results', []):
    props = page['properties']
    name = props['상호명']['title'][0]['plain_text']
    address = props['주소']['rich_text'][0]['plain_text']
    
    # 주소를 좌표로 변환 (지오코딩)
    loc = geolocator.geocode(address)
    if loc:
        folium.Marker([loc.latitude, loc.longitude], popup=name, tooltip=name).add_to(m)
        print(f"추가 완료: {name}")

m.save("map.html")
print("완료! 'map.html' 파일을 열어보세요.")