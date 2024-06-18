import pandas as pd
from kmodes.kprototypes import KPrototypes
import joblib

from clothes_kmodes.utils import load_df

import clothes_kmodes.clothes_enum as CLTH
import clothes_kmodes.config.config as cfg

# 범주형과 수치형 컬럼 분리
categorical_cols = ['나이', '성별', '스타일', '일 평균 기상',
                    '상의 색상', '상의 프린트', '상의 소재', '상의 기장', '상의 카테고리',
                    '하의 색상', '하의 프린트', '하의 소재', '하의 기장', '하의 카테고리']

numerical_cols = ['일 평균 기온', '일 평균 습도', '일 평균 풍속']

"""
사용자 정보(나이, 성별, 스타일, 일 평균 기온, 일 평균 기상, 일 평균 습도, 일 평균 풍속)에 해당하는
정보를 입력하여 원하는 상의 OR 하의를 추천함

(주의)
user_info에 값을 넣을때는 "나이, 성별, 스타일, 일 평균 기온, 일 평균 기상, 일 평균 습도, 일 평균 풍속" 순서를 지켜서 넣을 것!!
"""
def predict(*args):
    print("a", args)
    if len(args) == 2 and isinstance(args[0], tuple) and isinstance(args[1], int):
        user_info, want_clothes_type = args
        new_data = load_df.get_from_user_info(user_info)

    elif len(args) == 3 and isinstance(args[0], tuple) and isinstance(args[1], tuple) and isinstance(args[2], int):
        user_info, other_info, want_clothes_type = args
        if want_clothes_type == CLTH.BOTTOM:
            new_data = load_df.get_from_user_info_and_top(user_info, other_info)
        else:
            new_data = load_df.get_from_user_info_and_bottom(user_info, other_info)

    print(new_data)

    # 모델을 저장할 파일 경로
    model_path = cfg.kproto_model_path

    # 모델 로드
    kproto = joblib.load(model_path)
    print("모델이 성공적으로 로드되었습니다.")

    # 새로운 데이터 포인트에 대한 클러스터 예측
    df = pd.read_csv(cfg.final_result_with_cluster_path)
    categorical_cols_indices = [df.columns.get_loc(col) for col in categorical_cols]
    cluster_for_new_data = kproto.predict(new_data, categorical=categorical_cols_indices)
    print(cluster_for_new_data)

    # 새로운 데이터 포인트의 클러스터에 해당하는 기존 클러스터 출력
    cluster_data = df[df['Cluster'] == cluster_for_new_data[0]]
    # print(f"새로운 데이터 포인트의 클러스터 ({cluster_for_new_data[0]})에 해당하는 데이터:")
    # print(cluster_data)
    
    return cluster_data

