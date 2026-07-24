import requests
import json

# 대한민국 행정동 단위 정밀 GeoJSON 데이터 (kostat 2013 기준)
url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/skorea_municipalities_geo.json"

response = requests.get(url)
data = response.json()

# 'name' 값에 '의정부'가 포함된 구역만 추출 (행정동 단위)
uijeongbu_dong_features = [feature for feature in data['features'] 
                           if '의정부' in feature['properties']['name']]

uijeongbu_geojson = {
    "type": "FeatureCollection",
    "features": uijeongbu_dong_features
}

with open('uijeongbu_dong.geojson', 'w', encoding='utf-8') as f:
    json.dump(uijeongbu_geojson, f, ensure_ascii=False)

print(f"의정부 행정동 경계 추출 완료! 총 {len(uijeongbu_dong_features)}개의 동이 저장되었습니다.")