import requests
import json

def get_coordinates(address):
    # 카카오 주소 검색 API URL
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    
    # 발급받은 REST API 키 입력 (KakaoAK 뒤에 한 칸 띄우고 키 붙여넣기)
    headers = {
        "Authorization": "KakaoAK xxx"
    }
    
    # API 요청
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result['documents']:
            # 가장 정확도가 높은 첫 번째 결과의 좌표 추출
            x = result['documents'][0]['x'] # 경도 (Longitude)
            y = result['documents'][0]['y'] # 위도 (Latitude)
            return float(x), float(y)
        else:
            return None, None
    else:
        print("에러 발생:", response.status_code)
        return None, None

# 사용 예시
address = "경기도 성남시 분당구 판교역로 166"
longitude, latitude = get_coordinates(address)
print(f"주소: {address}")
print(f"경도: {longitude}, 위도: {latitude}")