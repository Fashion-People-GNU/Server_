from clothes_kmodes.server_api import run
import clothes_kmodes.clothes_enum as CLTH
import clothes_kmodes.config.config as cfg
import json
import os
from joblib import load

# 현재 파일의 디렉토리 경로를 기준으로 모델 경로 설정
base_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(base_dir, 'datasets/kproto_model.joblib')

# 모델 로드
try:
    model = load(model_path)
except FileNotFoundError:

    """
    user_info에 값을 넣을때는 "나이, 성별, 스타일, 일 평균 기온, 일 평균 기상, 일 평균 습도, 일 평균 풍속" 순서를 지켜서
    """


def data_sort(clothes, type):
    # 데이터 정렬
    # '상의 카테고리'와 '상의 색상'의 빈도수를 계산하여 데이터 프레임에 추가
    category_counts = clothes[f'{type} 카테고리'].value_counts()
    color_counts = clothes[f'{type} 색상'].value_counts()

    clothes['category_count'] = clothes[f'{type} 카테고리'].map(category_counts)
    clothes['color_count'] = clothes[f'{type} 색상'].map(color_counts)

    # 빈도수 기준으로 정렬
    df_sorted = clothes.sort_values(by=['category_count', 'color_count'], ascending=[False, False]).drop(
        columns=['category_count', 'color_count'])

    return df_sorted


def top_recommend(user_info, clothes_attributes, selected_info):
    if selected_info == None:
        top_clothes = run.predict(user_info, CLTH.TOP)
    else:
        top_clothes = run.predict(user_info, selected_info, CLTH.TOP)

    # 데이터 정렬
    df_sorted = data_sort(top_clothes, "상의")
    print(df_sorted)
    try:
        for cloth in df_sorted.iloc:
            if cloth["나이"] == user_info[0] and cloth["성별"] == user_info[1] and cloth["스타일"] == user_info[2]:
                for attributes in clothes_attributes:
                    if cloth["상의 카테고리"] == attributes[0] and cloth["상의 색상"] == attributes[1]:  # and cloth["상의 기장"] == attributes[2] and cloth["상의 소재"] == attributes[3] and cloth["상의 프린트"] == attributes[4]:
                        top_id = attributes[5]
                        top_color = cloth["상의 색상"]
                        top_print = cloth["상의 프린트"]
                        top_material = cloth["상의 소재"]
                        top_length = cloth["상의 기장"]
                        top_category = cloth["상의 카테고리"]
                        break

        return True, (top_color, top_print, top_material, top_length, top_category, top_id)
    except:
        try:
            for cloth in df_sorted.iloc:
                if cloth["나이"] == user_info[0] and cloth["성별"] == user_info[1] and cloth["스타일"] == user_info[2]:
                    for attributes in clothes_attributes:
                        if cloth["상의 카테고리"] == attributes[0]:
                            top_id = attributes[5]
                            top_color = cloth["상의 색상"]
                            top_print = cloth["상의 프린트"]
                            top_material = cloth["상의 소재"]
                            top_length = cloth["상의 기장"]
                            top_category = cloth["상의 카테고리"]
                            break

            return True, (top_color, top_print, top_material, top_length, top_category, top_id)
        except:
            return False, None


def bottom_recommend(user_info, clothes_attributes, selected_info):
    # 하의 추천
    #bottom_clothes = run.predict(user_info, selected_info, CLTH.BOTTOM)

    if selected_info == None:
        bottom_clothes = run.predict(user_info, CLTH.TOP)
    else:
        bottom_clothes = run.predict(user_info, selected_info, CLTH.TOP)

    # 데이터 정렬
    df_sorted = data_sort(bottom_clothes, "하의")

    try:
        for cloth in df_sorted.iloc:
            if cloth["나이"] == user_info[0] and cloth["성별"] == user_info[1] and cloth["스타일"] == user_info[2]:
                for attributes in clothes_attributes:
                    if cloth["하의 카테고리"] == attributes[0] and cloth["하의 색상"] == attributes[1]:  # and cloth["하의 기장"] == attributes[2] and cloth["하의 소재"] == attributes[3] and cloth["하의 프린트"] == attributes[4]:
                        bottom_id = attributes[5]
                        bottom_color = cloth["하의 색상"]
                        bottom_print = cloth["하의 프린트"]
                        bottom_material = cloth["하의 소재"]
                        bottom_length = cloth["하의 기장"]
                        bottom_category = cloth["하의 카테고리"]
                        break

        return True, (bottom_color, bottom_print, bottom_material, bottom_length, bottom_category, bottom_id)
    except:
        try:
            for cloth in df_sorted.iloc:
                if cloth["나이"] == user_info[0] and cloth["성별"] == user_info[1] and cloth["스타일"] == user_info[2]:
                    for attributes in clothes_attributes:
                        if cloth["하의 카테고리"] == attributes[0]:
                            bottom_id = attributes[5]
                            bottom_color = cloth["하의 색상"]
                            bottom_print = cloth["하의 프린트"]
                            bottom_material = cloth["하의 소재"]
                            bottom_length = cloth["하의 기장"]
                            bottom_category = cloth["하의 카테고리"]
                            break

            return True, (bottom_color, bottom_print, bottom_material, bottom_length, bottom_category, bottom_id)
        except:
            return False, None


def both_recommend(user_info, clothes_attributes):
    ret, top_clothes = top_recommend(user_info, clothes_attributes, None)
    if ret:
        top_id = top_clothes[-1]
        top_clothes = top_clothes[:-1]
        try:
            bottom_clothes = run.predict(user_info, top_clothes, CLTH.BOTTOM)
            # 데이터 정렬
            df_sorted = data_sort(bottom_clothes, "하의")

            for cloth in df_sorted.iloc:
                if cloth["나이"] == user_info[0] and cloth["성별"] == user_info[1] and cloth["스타일"] == user_info[2]:
                    for attributes in clothes_attributes:
                        if cloth["상의 카테고리"] == top_clothes[4] and cloth["상의 색상"] == top_clothes[0]:
                            # print(cloth)
                            if cloth["하의 카테고리"] == attributes[0] and cloth["하의 색상"] == attributes[1]:  # and cloth["하의 기장"] == attributes[2] and cloth["하의 소재"] == attributes[3] and cloth["하의 프린트"] == attributes[4]:
                                bottom_id = attributes[5]
                                bottom_color = cloth["하의 색상"]
                                bottom_print = cloth["하의 프린트"]
                                bottom_material = cloth["하의 소재"]
                                bottom_length = cloth["하의 기장"]
                                bottom_category = cloth["하의 카테고리"]
                                break

            print(bottom_color, bottom_print, bottom_material, bottom_length, bottom_category, bottom_id)
            return top_id, bottom_id
        except:
            return top_id, "하의 없음"
    else:
        return "상의 없음", "하의 없음"


def main(age, sex, style, temperatures, weather, humidity, wind_speed, recommend_select, selected_info, user_clothes):
    user_info = (age, sex, style, temperatures, weather, humidity, wind_speed)
    # 하의를 먼저할지 상의를 먼저할지는 CLTH.TOP, CLTH.BOTTOM 으로 설정하면 됨

    # ==========================================================================================
    # 각 항목의 필요한 필드를 추출하여 2차원 배열로 저장
    clothes_attributes = [[item['type'], item['color'], item['length'], item['material'], item['printing'], item['id']]
                          for item in user_clothes]

    # ==========================================================================================
    # 전체 추천
    if recommend_select == 0:
        print("============================================= 전체 추천 =============================================")
        return both_recommend(user_info, clothes_attributes)
    # 상의 추천
    elif recommend_select == 1:
        print("============================================= 상의 추천 =============================================")
        return top_recommend(user_info, clothes_attributes, selected_info)
    # 하의 추천
    elif recommend_select == 2:
        print("============================================= 하의 추천 =============================================")
        return bottom_recommend(user_info, clothes_attributes, selected_info)


if __name__ == "__main__":
    age = "30대"  # 사용자 입력 데이터
    sex = "남성"  # 사용자 입력 데이터
    style = "스트리트"  # 사용자 입력 데이터
    temperatures = 28.4  # 오늘 기온
    weather = "비"  # 오늘 기상
    humidity = 55.3  # 오늘 습도
    wind_speed = 1.6  # 오늘 풍속
    recommend_select = 1  # 전체 추천[0] / 상의 추천[1] / 하의 추천[2]

    # 사용자가 선택한 옷 속성
    cloth_color = "블랙"  # 색상
    cloth_print = "플로럴"  # 프린트
    cloth_material = "우븐"  # 소재
    cloth_length = "노멀"  # 길이
    cloth_category = "재킷"  # 카테고리
    selected_info = (cloth_color, cloth_print, cloth_material, cloth_length, cloth_category)

    user_clothes = ""

    # 전체 추천
    if recommend_select == 0:
        result = main(age, sex, style, temperatures, weather, humidity, wind_speed, recommend_select, user_clothes, None)
    # 부분 추천
    else:
        result = main(age, sex, style, temperatures, weather, humidity, wind_speed, recommend_select, selected_info, user_clothes)[1][
            5]