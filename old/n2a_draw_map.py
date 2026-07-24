import folium

# 선생님의 현재 위치(의정부)를 기준으로 지도 생성
m = folium.Map(location=[37.7381, 127.0339], zoom_start=13)

# 맛집 데이터 (위에서 가져온 리스트입니다)
restaurants = [
    {"name": "락궁 (신흥대점)", "lat": 37.7285, "lon": 127.0435},
    {"name": "지동관 (의정부 시내)", "lat": 37.7397, "lon": 127.0427},
    {"name": "신화 짬뽕 (신곡동)", "lat": 37.7335, "lon": 127.0545},
    # ... 나머지 좌표도 같은 형식으로 넣어주시면 됩니다.
]

# 지도에 마커 추가
for res in restaurants:
    folium.Marker(
        [res["lat"], res["lon"]],
        popup=res["name"],
        tooltip=res["name"]
    ).add_to(m)

# 지도를 'map.html'로 저장
m.save("map.html")
print("지도 파일(map.html)이 생성되었습니다! 파일을 열어보세요.")