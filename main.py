import json

import pandas as pd
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, storage
import re
import logging as log

import top_bottom_chg
from clothes_detector import detector
import os
import requests
from datetime import datetime, timedelta
import urllib.parse

# 현재 파일의 디렉토리 경로를 기준으로 clothes_kmodes와 clothes_detector 폴더의 절대 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))

import clothes_kmodes.main as clothes_main

cred = credentials.Certificate("flask-server/firebase/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

RESULT_FOLDER = "clothes_detector/result/"
DATASET_FOLDER = "clothes_detector/dataset/"
app.config['UPLOAD_FOLDER'] = DATASET_FOLDER


# 루트
@app.route('/')
def hello_world():
    return jsonify(), 404


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


@app.route('/weather/get', methods=['GET'])
def weather():
    lat = float(request.args.get('lat'))
    lon = float(request.args.get('lon'))

    if not lat or not lon:
        return jsonify({'error': 'Latitude and Longitude are required'}), 400

    try:
        nx, ny, region_1, region_2, region_3 = find_closest_region(lat, lon)
        log.info(f"Converted lat/lon to grid coordinates: nx={nx}, ny={ny}")
    except TypeError:
        return jsonify({'error': 'Failed to convert lat/lon to grid coordinates'}), 500

    if nx is None or ny is None:
        return jsonify({'error': 'Failed to convert lat/lon to grid coordinates'}), 500

    weather_info = get_current_weather_info(nx, ny, region_1, region_2, region_3)

    if weather_info is None:
        return jsonify({'error': 'Failed to retrieve weather information'}), 500

    response_data = {
        'region': weather_info['region'],
        'currentTemp': weather_info['currentTemp'],
        'maxTemp': weather_info['maxTemp'],
        'minTemp': weather_info['minTemp'],
        'humidity': weather_info['humidity'],
        'weather': weather_info['weather'],
        'windSpeed': weather_info['windSpeed']
    }

    return jsonify(response_data), 200


# 옷 추천
@app.route('/clothes/propose', methods=['GET'])
def clothes_propose():
    try:
        uid = request.args.get('uid')
        user_doc_ref = db.collection('users').document(uid)
        user_doc = user_doc_ref.get()
        user_data = user_doc.to_dict()

        user_closet_doc = user_doc_ref.collection('closet').get()
        user_clothes = []

        age = user_data['age']
        sex = user_data['sex']

        style = request.args.get('style')
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        recommend_flag = int(request.args.get('recommendFlag'))
        print(f"recommend_flag = {recommend_flag}")
        recommend_select = 0

        if recommend_flag == 0:
            recommend_select = 0
            for i in user_closet_doc:
                user_clothes.append({"id": i.id, **i.to_dict()})

        elif recommend_flag == 1:
            cloth_id = request.args.get('clothId')

            doc_ref = db.collection('users').document(uid).collection('closet').document(cloth_id)
            doc = doc_ref.get()
            doc_data = doc.to_dict()

            cloth_color = doc_data['color']
            cloth_print = doc_data['printing']
            cloth_material = doc_data['style']
            cloth_length = doc_data['length']
            cloth_category = doc_data['type']

            if cloth_category in top_bottom_chg.top:
                recommend_select = 2
                for i in user_closet_doc:
                    d = i.to_dict()
                    if d['type'] in top_bottom_chg.bottom:
                        user_clothes.append({"id": i.id, **i.to_dict()})
            elif cloth_category in top_bottom_chg.bottom:
                recommend_select = 1
                for i in user_closet_doc:
                    d = i.to_dict()
                    if d['type'] in top_bottom_chg.top:
                        user_clothes.append({"id": i.id, **i.to_dict()})

        if not age or not sex or not style:
            return jsonify({'error': 'Age, Sex, and Style are required'}), 400

        if not lat or not lon:
            return jsonify({'error': 'Latitude and Longitude are required'}), 400

        if recommend_select not in [0, 1, 2]:
            return jsonify({'error': 'Invalid recommend_select value. Use 0 for both recommendation, 1 for top recommendation, 2 for bottom recommendation'}), 400

        if recommend_select in [1, 2] and (not cloth_color or not cloth_print or not cloth_material or not cloth_length or not cloth_category):
            return jsonify({'error': 'Cloth attributes are required for partial recommendation'}), 400

        # 위치를 통해 날씨 정보 가져오기
        nx, ny, region_1, region_2, region_3 = find_closest_region(lat, lon)

        current_weather_info = get_current_weather_info(nx, ny, region_1, region_2, region_3)

        if current_weather_info is None:
            return jsonify({'error': 'Failed to retrieve current weather information'}), 500

        temperatures = current_weather_info['currentTemp']
        weather = current_weather_info['weather']
        humidity = current_weather_info['humidity']
        wind_speed = current_weather_info['windSpeed']

        selected_info = (
            cloth_color, cloth_print, cloth_material, cloth_length, cloth_category
        ) if recommend_select in [1, 2] else None

        print(user_clothes)
        # 옷 추천 모델 호출
        result = clothes_main.main(age, sex, style, temperatures, weather, humidity, wind_speed, recommend_select, selected_info, user_clothes)

        if recommend_select == 0:  # 전체 추천
            top_id, bottom_id = result
            data = []
            if top_id != "상의 없음":
                doc_ref = db.collection('users').document(uid).collection('closet').document(top_id)
                doc = doc_ref.get()
                doc_data = doc.to_dict()
                data.append(doc_data)

            if bottom_id != "하의 없음":
                doc_ref = db.collection('users').document(uid).collection('closet').document(bottom_id)
                doc = doc_ref.get()
                doc_data = doc.to_dict()
                data.append(doc_data)

            response_data = jsonify(data), 200
        elif recommend_select == 1:  # 상의 추천
            success, top_clothes = result
            print(f"success = {success}, top_clothes = {top_clothes}")
            if success:
                top_color, top_print, top_material, top_length, top_category, top_id = top_clothes
                doc_ref = db.collection('users').document(uid).collection('closet').document(top_id)
                doc = doc_ref.get()

                response_data = jsonify(doc.to_dict()), 200
            else:
                response_data = jsonify({}), 200
        elif recommend_select == 2:  # 하의 추천
            success, bottom_clothes = result
            print(f"success = {success}, top_clothes = {bottom_clothes}")
            if success:
                bottom_color, bottom_print, bottom_material, bottom_length, bottom_category, bottom_id = bottom_clothes
                doc_ref = db.collection('users').document(uid).collection('closet').document(bottom_id)
                doc = doc_ref.get()

                response_data = jsonify(doc.to_dict()), 200
            else:
                response_data = jsonify({}), 200

        return response_data
    except Exception as e:
        print(f"예외 발생: {e}")
        return jsonify({'error': str(e)}), 500


# 옷 id -> 해당 옷 정보
@app.route('/clothes/info/get', methods=['GET'])
def get_image_url():
    uid = request.args.get('uid')
    cloth_id = request.args.get('clothId')

    doc_ref = db.collection('users').document(uid).collection('closet').document(cloth_id)

    doc = doc_ref.get()

    if doc.exists:
        doc_data = doc.to_dict()
        return jsonify(doc_data), 200
    else:
        return jsonify({'error': 'get image url failed'}), 500


# 사용자 정보 업데이트
@app.route('/user/info/update', methods=['POST'])
def user_info_update():
    try:
        uid = request.form.get('uid')
        age = request.form.get('age')
        sex = request.form.get('sex')

        print(f"uid = {uid}, age = {age}, sex = {sex}")

        doc_ref = db.collection('users').document(uid)

        doc_ref.update({
            'age': age,
            'sex': sex,
        })

        return jsonify({"message": "update successful"}), 200
    except:
        return jsonify({"error": "Bad Request"}), 400


# 사용자 정보 불러오기
@app.route('/user/info/get', methods=['GET'])
def user_info_get():
    uid = request.args.get('uid')

    if uid is None:
        return jsonify({'error': 'uid is None'}), 400

    doc_ref = db.collection('users').document(uid)
    doc = doc_ref.get()
    doc_data = doc.to_dict()

    if not 'age' in doc_data:
        doc_data['age'] = ""
        doc_data['sex'] = ""

    log.info(str(doc_data))
    return jsonify(doc_data), 200


# 옷 추가
@app.route('/clothes/add', methods=['POST'])
def add_clothes():
    if 'image' not in request.files:
        log.error('No image file found')
        return jsonify({'error': 'No image file found'}), 400
    uid = request.form.get('uid')
    image_file = request.files.get('image')
    image_name = request.form.get('imageName').replace("\"", "")
    cloth_name = None

    if image_file.filename == '':
        log.error('No image file name')
        return jsonify({'error': 'No image file name'}), 400

    # 파일 저장
    if image_file:
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename))

    uid = re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z\s]", "", uid)

    # result 폴더 정리
    result_folder_clear(uid)

    # 모듈 실행
    opt = detector.parse_opt()
    result = detector.main(opt)
    keys = result.keys()

    for i in keys:
        if str(i).replace(uid, '') == '':
            return jsonify({'error': 'no detections'}), 400

        if str(i).find(uid) != -1:
            cloth_name = str(i).replace(uid, '')
            cloth_type = str(i).split('_')[1]

            if cloth_name is None:
                return jsonify({'error': 'module execution failed'}), 503

            # 이미지를 Google Cloud Storage에 업로드
            result_image = os.path.join(RESULT_FOLDER, str(i) + '.jpg')
            bucket = storage.bucket('todays-clothes-1100f.appspot.com')
            blob = bucket.blob(f'images/{uid}/{cloth_type + "_" + image_name}')
            with open(result_image, 'rb') as file:
                blob.upload_from_file(file)

            # 이미지 URL 생성
            image_url = blob.public_url

            detail = result.get(i)
            color = detail.get('color')
            length = detail.get('length')
            material = detail.get('material')
            printing = detail.get('print')
            style = detail.get('style')
            add_date = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Firestore에 이미지 URL과 기타 정보 저장
            doc_ref = db.collection('users').document(uid).collection('closet').document()
            doc_ref.set({
                'type': cloth_type,
                'imageUrl': image_url,
                'imageName': image_name,
                'color': color,
                'length': length,
                'material': material,
                'printing': printing,
                'style': style,
                'addDate': add_date
            })

    response_data = {
        'message': 'Data received successfully',
        'uid': uid,
        'image_name': image_name
    }
    log.info(str(response_data))
    return jsonify({'message': 'clothes add successfully'}), 200


def result_folder_clear(uid):
    for file_name in os.listdir(RESULT_FOLDER):
        if uid == file_name.split('_')[0]:
            file_path = os.path.join(RESULT_FOLDER, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)


# 옷장 가져오기
@app.route('/clothes/get/<uid>', methods=['GET'])
def get_closet(uid):
    try:
        doc_ref = db.collection('users').document(uid).collection('closet')
        docs = doc_ref.get()
        closet_data = []
        for doc in docs:
            data = {'id': doc.id, **doc.to_dict()}
            closet_data.append(data)

        log.info(str(closet_data))
        return jsonify(closet_data), 200
    except Exception as e:
        log.error(str(e))
        return jsonify({'error': 'failed get closet'}), 500


# 옷 삭제
@app.route('/clothes/delete/<uid>/<cloth_id>', methods=['DELETE'])
def delete_closet(uid, cloth_id):
    try:
        doc_ref = db.collection('users').document(uid).collection('closet').document(cloth_id)
        doc = doc_ref.get()

        if doc.exists:
            image_url = doc.get('imageUrl')
            if image_url:
                # Storage URL에서 파일 경로 추출
                file_path = "/".join([str(p) for p in image_url.split('/')[-3:]])
                decoded_file_path = urllib.parse.unquote(file_path)

                # Storage에서 파일 삭제
                bucket = storage.bucket('todays-clothes-1100f.appspot.com')
                blob = bucket.blob(decoded_file_path)
                if blob.exists():
                    blob.delete()
                else:
                    log.error('image not found in storage')
                    return jsonify({'error': 'image not found in storage'}), 400

            doc_ref.delete()

            log.info('Data and file deleted successfully')
            return jsonify({'message': 'Data and file deleted successfully'}), 200
        else:
            log.error('Document not found')
            return jsonify({'error': 'Document not found'}), 404

    except Exception as e:
        log.error(str(e))
        return jsonify({'error': "failed delete cloth"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

