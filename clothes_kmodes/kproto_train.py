import pandas as pd
from kmodes.kprototypes import KPrototypes
import joblib
import config.config as cfg

# 데이터 로드
df = pd.read_csv(cfg.final_result_path)

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
print(clusters)

# 클러스터 할당 결과
df['Cluster'] = clusters

# 학습된 모델 저장
model_path = cfg.kproto_model_path
joblib.dump(kproto, model_path)
print("모델이 성공적으로 학습되고 저장되었습니다.")

# 클러스터가 추가된 데이터프레임 저장
final_result_with_clusters_path = cfg.final_result_with_cluster_path
df.to_csv(final_result_with_clusters_path, index=False)
print("클러스터가 추가된 데이터프레임이 성공적으로 저장되었습니다.")

# 클러스터별 데이터 출력 및 개수 확인
for cluster in range(kproto.n_clusters):
    cluster_data = df[df['Cluster'] == cluster]
    print(f"클러스터 {cluster}의 데이터 ({len(cluster_data)}개):")
    print(cluster_data)
    print("\n")  # 클러스터별로 구분하기 위해 줄바꿈 추가

# 각 클러스터에 속하는 데이터의 개수 출력
cluster_counts = df['Cluster'].value_counts().sort_index()
print("각 클러스터에 속하는 데이터의 개수:")
print(cluster_counts)
