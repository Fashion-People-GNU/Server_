import numpy as np
import pandas as pd

# CSV 파일 경로 설정
weather_csv_path = r"D:\Development\Pycharm Projects\FashionPeople\datasets\musinsa_weather.csv"
musinsa_feature_csv_path = r"D:\Development\Pycharm Projects\FashionPeople\datasets\musinsa_result_1.csv"

# 필요한 컬럼들 정의
final_col = ["나이", "성별", "스타일", "일 평균 기온", "일 평균 기상", "일 평균 습도", "일 평균 풍속",
             "상의 카테고리", "상의 색상", "상의 기장", "상의 소재", "상의 프린트",
             "하의 카테고리", "하의 색상", "하의 기장", "하의 소재", "하의 프린트"]

# CSV 데이터 로드
weather_data = pd.read_csv(weather_csv_path)
feature_data = pd.read_csv(musinsa_feature_csv_path)

# feature_data에서 파일명에서 마지막 요소 추출
feature_data['파일명_추출'] = feature_data['파일명'].apply(lambda x: x.split('/')[-1])

# weather_data에서 파일명과 비교하여 병합
merged_data = feature_data.merge(weather_data, left_on='파일명_추출', right_on='이미지 파일명', suffixes=('', '_weather'))

# 결측값 처리: 수치형 열의 결측값은 평균값으로, 범주형 열의 결측값은 최빈값으로 대체
for col in final_col:
    if col in merged_data.columns:
        if merged_data[col].dtype == 'O':  # 범주형 데이터
            merged_data[col].fillna(merged_data[col].mode()[0], inplace=True)
        else:  # 수치형 데이터
            merged_data[col].fillna(merged_data[col].mean(), inplace=True)

# 필요한 컬럼 선택
final_data = merged_data[final_col]

# 새로운 CSV 파일로 저장
final_csv_path = r"D:\Development\Pycharm Projects\FashionPeople\datasets\final_result.csv"
final_data.to_csv(final_csv_path, index=False)

print("CSV 파일이 성공적으로 생성되었습니다.")
