import pandas as pd
import logging as log

import requests
from datetime import datetime, timedelta


# CSV 파일 로드
CSV_FILE_PATH = r'data/lat_lon_grid_utf8.csv'
grid_data = pd.read_csv(CSV_FILE_PATH)


def find_closest_region(lat, lon):
    grid_data['경도(초/100)'] = grid_data['경도(초/100)'].astype(float)
    grid_data['위도(초/100)'] = grid_data['위도(초/100)'].astype(float)

    closest_row = grid_data.iloc[((grid_data['경도(초/100)'] - lon).abs() + (grid_data['위도(초/100)'] - lat).abs()).idxmin()]

    region_1 = closest_row['1단계']
    region_2 = closest_row['2단계']
    region_3 = closest_row['3단계']
    nx = closest_row['격자 X']
    ny = closest_row['격자 Y']

    return nx, ny, region_1, region_2, region_3


# 가장 가까운 예보 시간을 계산 (초단기예보 및 실황용)
def get_ultrashort_base_time():
    now = datetime.now()
    base_time = now - timedelta(minutes=(now.minute % 10) + 10)
    if base_time.minute >= 40:
        base_time = base_time.replace(minute=30)
    else:
        base_time = base_time.replace(minute=30) - timedelta(hours=1)
    base_date = base_time.strftime("%Y%m%d")
    base_time = base_time.strftime("%H%M")
    return base_date, base_time


# 가장 가까운 예보 시간을 계산 (단기예보용)
def get_short_base_time():
    now = datetime.now()
    hour = now.hour
    if hour < 2:
        base_time = "2300"
        base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
    elif hour < 5:
        base_time = "0200"
        base_date = now.strftime("%Y%m%d")
    elif hour < 8:
        base_time = "0500"
        base_date = now.strftime("%Y%m%d")
    elif hour < 11:
        base_time = "0800"
        base_date = now.strftime("%Y%m%d")
    elif hour < 14:
        base_time = "1100"
        base_date = now.strftime("%Y%m%d")
    elif hour < 17:
        base_time = "1400"
        base_date = now.strftime("%Y%m%d")
    elif hour < 20:
        base_time = "1700"
        base_date = now.strftime("%Y%m%d")
    else:
        base_time = "2000"
        base_date = now.strftime("%Y%m%d")
    return base_date, base_time


# 현재 날씨 정보 가져오기 (초단기실황)
def get_current_weather_info(nx, ny, region_1, region_2, region_3):
    base_date, base_time = get_ultrashort_base_time()
    serviceKey = "T38Xs/J3skbx5QujsH/ZfPUIDlfyGqvCcjw+DekGON1+Ul+DXg1KueJlW0zUHGEIpidKOPzgyiDqAM8jQZ/dUg=="

    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    params = {
        "serviceKey": serviceKey,
        "numOfRows": "1000",
        "pageNo": "1",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        try:
            data = response.json()
            if data['response']['header']['resultCode'] == '00':
                items = data['response']['body']['items']['item']

                current_temp = None
                humidity = None
                wind_speed = None
                weather_description = None
                sky_code = None
                visibility = None  # 가시거리(안개)

                for item in items:
                    category = item['category']
                    fcst_value = item['obsrValue']

                    try:
                        fcst_value = float(fcst_value)
                    except ValueError:
                        continue

                    if category == 'T1H':  # 기온
                        current_temp = fcst_value
                    elif category == 'REH':  # 습도
                        humidity = fcst_value
                    elif category == 'WSD':  # 풍속
                        wind_speed = fcst_value
                    elif category == 'PTY':  # 강수형태
                        weather_description = int(fcst_value)
                    elif category == 'SKY':  # 구름상태
                        sky_code = int(fcst_value)
                    elif category == 'VVV':  # 가시거리
                        visibility = fcst_value

                weather = None
                if weather_description in [1, 2, 5, 6]:  # 비, 비/눈, 빗방울, 빗방울눈날림
                    weather = '비'
                elif weather_description in [3, 7]:  # 눈, 눈날림
                    weather = '눈'
                elif sky_code == 1:  # 맑음
                    weather = '맑음'
                elif sky_code == 3:  # 구름많음
                    weather = '구름 많음'
                elif sky_code == 4:  # 흐림
                    weather = '흐림'
                elif humidity >=70:
                        weather = '구름많음'
                elif visibility is not None and visibility < 1:
                    weather = '안개'
                else:
                    weather = '맑음'


                # 단기예보에서 최고/최저 기온 가져오기
                base_date, base_time = get_short_base_time()
                url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
                params = {
                    "serviceKey": serviceKey,
                    "numOfRows": "1000",
                    "pageNo": "1",
                    "dataType": "JSON",
                    "base_date": base_date,
                    "base_time": base_time,
                    "nx": nx,
                    "ny": ny
                }
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data['response']['header']['resultCode'] == '00':
                            items = data['response']['body']['items']['item']

                            max_temp = None
                            min_temp = None

                            for item in items:
                                category = item['category']
                                fcst_value = item['fcstValue']
                                fcst_time = item['fcstTime']

                                try:
                                    fcst_value = float(fcst_value)
                                except ValueError:
                                    continue

                                if category == 'TMX':  # 최고기온
                                    if max_temp is None or fcst_value > max_temp:
                                        max_temp = fcst_value
                                elif category == 'TMN':  # 최저기온
                                    if min_temp is None or fcst_value < min_temp:
                                        min_temp = fcst_value

                            weather_info = {
                                "region": f"{region_1} {region_2}",
                                "currentTemp": current_temp,
                                "maxTemp": max_temp,
                                "minTemp": min_temp,
                                "humidity": humidity,
                                "weather": weather,
                                "windSpeed": wind_speed
                            }
                            return weather_info
                        else:
                            log.error(f"Error: {data['response']['header']['resultMsg']}")
                            return None
                    except requests.exceptions.JSONDecodeError as e:
                        log.error(f"JSON decoding failed: {e} - Response text: {response.text}")
                        return None
                else:
                    log.error(f"HTTP error {response.status_code}")
                    return None
            else:
                log.error(f"Error: {data['response']['header']['resultMsg']}")
                return None
        except requests.exceptions.JSONDecodeError as e:
            log.error(f"JSON decoding failed: {e} - Response text: {response.text}")
            return None
    else:
        log.error(f"HTTP error {response.status_code}")
        return None