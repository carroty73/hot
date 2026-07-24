import streamlit as st
import pandas as pd
import numpy as np

st.title("📍 당근이의 맛집 지도")

# 맛집의 위도, 경도 데이터 (예시)
map_data = pd.DataFrame(
    np.array([[37.5665, 126.9780], [37.5512, 126.9882]]), # 서울 시청 근처, 남산 근처
    columns=['lat', 'lon']
)

# 지도 그리기
st.map(map_data)

# 실행 방법 streamlit run app.py