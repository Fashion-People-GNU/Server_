import pandas as pd
from kmodes.kprototypes import KPrototypes

# 데이터 로드
df = pd.read_csv(rf'/datasets/final_result.csv')

# 범주형과 수치형 컬럼 분리
categorical_cols = ['나이', '성별', '스타일', '일 평균 기상',
                    '상의 색상', '상의 프린트', '상의 소재', '상의 기장', '상의 카테고리',
                    '하의 색상', '하의 프린트', '하의 소재', '하의 기장', '하의 카테고리']

numerical_cols = ['일 평균 기온', '일 평균 습도', '일 평균 풍속']

# 범주형과 수치형 컬럼 인덱스 확인
categorical_cols_indices = [df.columns.get_loc(col) for col in categorical_cols]

# 클러스터의 수를 줄이고, 초기화 방법을 'Cao'로 변경하며, 초기화 시도 횟수를 증가
kproto = KPrototypes(n_clusters=20, init='Cao', n_init=10, verbose=2)
clusters = kproto.fit_predict(df, categorical=categorical_cols_indices)

# 클러스터 할당 결과
df['Cluster'] = clusters

# 클러스터 중심점 출력
print(kproto.cluster_centroids_)

# 데이터프레임의 생략 없이 모든 행과 열을 출력하도록 설정
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)


# 데이터프레임의 첫 몇 줄을 출력하여 클러스터 할당 확인
print(df.head())

# 데이터프레임의 전체를 출력하여 클러스터 할당 확인
print(df)


# 새로운 데이터 포인트 생성
new_data = pd.DataFrame([
    {
        '나이': 30,
        '성별': '여성',
        '스타일': '캐주얼',
        '일 평균 기온': 20,
        '일 평균 기상': '맑음',
        '일 평균 습도': 50,
        '일 평균 풍속': 3,
        '상의 색상': '없음',
        '상의 프린트': '없음',
        '상의 소재': '없음',
        '상의 기장': '없음',
        '상의 카테고리': '없음',
        '하의 색상': '블루',
        '하의 프린트': '호피',
        '하의 소재': '스웨이드',
        '하의 기장': '크롭',
        '하의 카테고리': '팬츠'
    }
])

# 새로운 데이터 포인트에 대한 클러스터 예측
cluster_for_new_data = kproto.predict(new_data, categorical=categorical_cols_indices)

print(new_data)

print(f'새로운 데이터 포인트의 클러스터: {cluster_for_new_data[0]}')


# 각 클러스터별로 데이터 출력
for cluster in range(kproto.n_clusters):
   print(f"클러스터 {cluster}의 데이터:")
   cluster_data = df[df['Cluster'] == cluster]
   print(cluster_data)
   print("\n")  # 클러스터별로 구분하기 위해 줄바꿈 추가

# 새로운 데이터 포인트의 클러스터에 해당하는 기존 클러스터 출력
cluster_data = df[df['Cluster'] == cluster_for_new_data[0]]
print(f"새로운 데이터 포인트의 클러스터 ({cluster_for_new_data[0]})에 해당하는 데이터:")
print(cluster_data)
