import requests

TOKEN = "xxx"
DATABASE_ID = "yyy"

url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    print("--- [당근강의실] 맛집 리스트 확인 ---")
    for page in data.get('results', []):
        try:
            # 노션 DB 상호명 속성 가져오기
            name = page['properties']['상호명']['title'][0]['plain_text']
            print(f"맛집 이름: {name}")
        except Exception as e:
            print(f"속성 읽기 실패: {e}")
else:
    print(f"에러 코드: {response.status_code}")
    print(response.text)