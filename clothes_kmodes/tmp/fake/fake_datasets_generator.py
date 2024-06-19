import pandas as pd
import numpy as np
import random

# Define the possible values for each column based on the provided details
ages = ['20대', '30대', '40대', '50대']
genders = ['남성', '여성']
styles = [
    '클래식', '매니시', '페미닌', '히피', '모던', '컨트리', '젠더리스', '스포티', '레트로', '밀리터리',
    '프레피', '톰보이', '로맨틱', '웨스턴', '소피스트', '리조트', '키치/키덜트', '스트리트',
    '섹시', '오리엔탈', '아방가르드', '힙합', '펑크'
]
average_temperatures = list(range(15, 31))
weather_conditions = ['맑음', '구름', '비', '눈']
average_humidities = list(range(10, 91, 10))
average_wind_speeds = list(range(1, 6))
colors = [
    '블랙', '화이트', '그레이', '레드', '핑크', '오렌지', '베이지', '브라운', '옐로우', '그린', '카키', '실버'
]
prints = [
    '체크', '스트라이프', '지그재그', '호피', '지브라', '도트', '카무플라쥬', '페이즐리', '아가일', '무지', '믹스'
]
materials = [
    '퍼', '무스탕', '스웨이드', '헤어니트', '코듀로이', '시퀸', '데님', '저지', '니트', '스판덱스'
]
lengths = [
    '크롭', '노멀', '롱', '미니', '니렝스', '미디', '발목', '맥시', '민소매', '반팔', '캡', '7부소매', '긴팔'
]
top_categories = [
    '탑', '블라우스', '티셔츠', '니트웨어', '셔츠', '브라탑', '후드티'
]
bottom_categories = [
    '청바지', '팬츠', '스커트', '레깅스', '조거팬츠'
]
outerwear_categories = [
    '코트', '재킷', '점퍼', '패딩', '베스트', '가디건', '짚업'
]
dress_categories = [
    '드레스', '점프수트'
]


# Generating a fake dataset
num_entries = 100  # Number of entries you want in the dataset
data = []

for _ in range(num_entries):
    age = random.choice(ages)
    gender = random.choice(genders)
    style = random.choice(styles)
    avg_temp = random.choice(average_temperatures)
    weather = random.choice(weather_conditions)
    humidity = random.choice(average_humidities)
    wind_speed = random.choice(average_wind_speeds)
    top_color, bottom_color = random.sample(colors, 2)
    top_print, bottom_print = random.sample(prints, 2)
    material = random.choice(materials)
    length = random.choice(lengths)
    top_category = random.choice(top_categories)
    bottom_category = random.choice(bottom_categories)

    # Append to the data list
    data.append([
        age, gender, style, avg_temp, weather, humidity, wind_speed,
        top_color, top_print, material, length, top_category,
        bottom_color, bottom_print, material, length, bottom_category
    ])

# Columns
columns = [
    '나이', '성별', '스타일', '일 평균 기온', '일 평균 기상', '일 평균 습도', '일 평균 풍속',
    '상의 색상', '상의 프린트', '상의 소재', '상의 기장', '상의 카테고리',
    '하의 색상', '하의 프린트', '하의 소재', '하의 기장', '하의 카테고리']

df = pd.DataFrame(data, columns=columns)


# Display the first few rows of the dataframe to check
print(df.head())

# Save the dataframe to a CSV file
df.to_csv('./fake_fashion_dataset.csv', index=False)



