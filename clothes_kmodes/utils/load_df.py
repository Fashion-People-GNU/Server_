import pandas as pd


def get_from_user_info(user_info: tuple):
    age, gender, style, temperature, weather, humidity, wind = user_info
    new_data = pd.DataFrame([
        {
            '나이': age,
            '성별': gender,
            '스타일': style,
            '일 평균 기온': temperature,
            '일 평균 기상': weather,
            '일 평균 습도': humidity,
            '일 평균 풍속': wind,
            '상의 색상': '없음',
            '상의 프린트': '없음',
            '상의 소재': '없음',
            '상의 기장': '없음',
            '상의 카테고리': '없음',
            '하의 색상': '없음',
            '하의 프린트': '없음',
            '하의 소재': '없음',
            '하의 기장': '없음',
            '하의 카테고리': '없음'
        }
    ])

    return new_data


def get_from_user_info_and_top(user_info: tuple, top_info: tuple):
    age, gender, style, temperature, weather, humidity, wind = user_info
    top_color, top_print, top_material, top_length, top_category = top_info

    new_data = pd.DataFrame([
        {
            '나이': age,
            '성별': gender,
            '스타일': style,
            '일 평균 기온': temperature,
            '일 평균 기상': weather,
            '일 평균 습도': humidity,
            '일 평균 풍속': wind,
            '상의 색상': top_color,
            '상의 프린트': top_print,
            '상의 소재': top_material,
            '상의 기장': top_length,
            '상의 카테고리': top_category,
            '하의 색상': '없음',
            '하의 프린트': '없음',
            '하의 소재': '없음',
            '하의 기장': '없음',
            '하의 카테고리': '없음'
        }
    ])

    return new_data


def get_from_user_info_and_bottom(user_info: tuple, bottom_info: tuple):
    age, gender, style, temperature, weather, humidity, wind = user_info
    bottom_color, bottom_print, bottom_material, bottom_length, bottom_category = bottom_info

    new_data = pd.DataFrame([
        {
            '나이': age,
            '성별': gender,
            '스타일': style,
            '일 평균 기온': temperature,
            '일 평균 기상': weather,
            '일 평균 습도': humidity,
            '일 평균 풍속': wind,
            '상의 색상': '없음',
            '상의 프린트': '없음',
            '상의 소재': '없음',
            '상의 기장': '없음',
            '상의 카테고리': '없음',
            '하의 색상': bottom_color,
            '하의 프린트': bottom_print,
            '하의 소재': bottom_material,
            '하의 기장': bottom_length,
            '하의 카테고리': bottom_category
        }
    ])

    return new_data
