import requests
import folium
from geopy.geocoders import Nominatim

# 설정
TOKEN = "xxx"
DATABASE_ID = "yyy"

# 이미지 파일 경로 (30x30 크기의 작은 투명 PNG가 좋습니다)
CARROT_ICON_IMAGE = "carrot.png"  # 당근 이미지
HUMINT_ICON_IMAGE = "humint.png"  # 휴민트 이미지

# 1. 데이터 가져오기
url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
response = requests.post(url, headers=headers).json()

# 2. 지도 초기화
m = folium.Map(location=[37.738060, 127.046110], zoom_start=15)
geolocator = Nominatim(user_agent="my_restaurant_map_image_custom")

title_html = '''
             <div style="position: fixed; 
                          top: 10px; left: 50px; width: 250px; height: 50px; 
                          z-index:9999; font-size:24px; font-weight:bold; 
                          color:black; background-color:rgba(255,255,255,0.7); 
                          padding: 10px; border-radius: 10px; border: 2px solid #ccc;
                          text-align: center;">
                          당근이의 의정부 맛집
             </div>
             '''
m.get_root().html.add_child(folium.Element(title_html))

# 3. 작성자별 그룹 생성
groups = {
    "당근이": folium.FeatureGroup(name="당근이"),
    "휴민트": folium.FeatureGroup(name="휴민트")
}

MARKER_WIDTH= 30
MARKER_HEIGHT= 30

# 4. 데이터 파싱 및 이미지 마커 추가
print("이미지 마커를 사용하여 지도 생성 중...")
for page in response.get('results', []):
    props = page['properties']
    name = props['상호명']['title'][0]['plain_text']
    address = props['주소']['rich_text'][0]['plain_text']
    
    # 작성자 확인 (값이 없을 경우 대비)
    author_prop = props.get('작성자', {})
    author = author_prop['select']['name'] if author_prop.get('select') else "기타"
    
    loc = geolocator.geocode(address)
    if loc:
        # 5. 작성자에 따라 이미지 아이콘 설정
        if author == "당근이":
            # 당근 이미지 사용
            custom_icon = folium.CustomIcon(CARROT_ICON_IMAGE, icon_size=(MARKER_WIDTH, MARKER_HEIGHT))
        elif author == "휴민트":
            # 휴민트 이미지 사용
            custom_icon = folium.CustomIcon(HUMINT_ICON_IMAGE, icon_size=(MARKER_WIDTH, MARKER_HEIGHT))
        else:
            # 기타 (그룹에 없거나 이미지가 없는 경우)
            custom_icon = folium.Icon(color='gray', icon='question-circle') # 기본 아이콘
            
        # 마커 추가
        marker = folium.Marker(
            [loc.latitude, loc.longitude],
            popup=f"{name} ({author})",
            icon=custom_icon # 커스텀 아이콘 적용
        )
        
        # 해당 작성자 그룹에 추가
        if author in groups:
            marker.add_to(groups[author])
        else:
            marker.add_to(m) # 그룹이 없으면 기본 지도에 표시
    else:
        print(f"주소 검색 실패: {name}, 주소: {address}")

# 6. 그룹과 레이어 컨트롤 추가
for group in groups.values():
    group.add_to(m)
folium.LayerControl().add_to(m)

m.save("index.html")
print("완료! 'index.html' 파일을 열어보세요.")