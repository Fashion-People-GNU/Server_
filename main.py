from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, storage
import re
import logging as log
from clothes_detector import detector
import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
from datetime import datetime

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
    return 'Hello World!'

#날씨 데이터 가져오기
@app.route('/weather', methods=['GET'])
def weather():
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    if not lat or not lon:
        return jsonify({'error': 'Latitude and Longitude are required'}), 400

    try:
        nx, ny = get_grid_coordinates(lat, lon)
        print(f"Converted lat/lon to grid coordinates: nx={nx}, ny={ny}")
    except TypeError:
        return jsonify({'error': 'Failed to convert lat/lon to grid coordinates'}), 500

    if nx is None or ny is None:
        return jsonify({'error': 'Failed to convert lat/lon to grid coordinates'}), 500

    weather_info = get_weather_info(nx, ny)

    if weather_info is None:
        return jsonify({'error': 'Failed to retrieve weather information'}), 500

    return jsonify(weather_info)

def get_grid_coordinates(lat, lon):
    serviceKey = "GotqwkNXTiKLasJDV44ifA"
    url = "https://apihub.kma.go.kr/api/typ01/cgi-bin/url/nph-dfs_xy_lonlat"
    params = {
        "lon": lon,
        "lat": lat,
        "help": "0",
        "authKey": serviceKey
    }

    response = requests.get(url, params=params)
    print(f"Request URL: {url}")
    print(f"Request parameters: {params}")
    print(f"Response status code: {response.status_code}")
    print(f"Response text: {response.text}")

    if response.status_code == 200:
        try:
            lines = response.text.splitlines()
            for line in lines:
                if not line.startswith('#'):
                    fields = line.split(',')
                    if len(fields) == 4:
                        lon, lat, x, y = fields
                        print(f"Longitude: {lon.strip()}, Latitude: {lat.strip()}, X: {x.strip()}, Y: {y.strip()}")
                        return x.strip(), y.strip()
        except Exception as e:
            print(f"Error parsing response: {e}")
            return None, None
    else:
        print(f"Error response: {response.status_code}, {response.text}")

    return None, None

def get_weather_info(nx, ny):
    serviceKey = "T38Xs/J3skbx5QujsH/ZfPUIDlfyGqvCcjw+DekGON1+Ul+DXg1KueJlW0zUHGEIpidKOPzgyiDqAM8jQZ/dUg=="
    base_date = datetime.now().strftime("%Y%m%d")
    base_time = "0200"

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
    print(f"Request URL: {url}")
    print(f"Request parameters: {params}")
    print(f"Weather API response status code: {response.status_code}")
    print(f"Weather API response text: {response.text}")

    if response.status_code == 200:
        try:
            data = response.json()
            print(data)  # 전체 응답 데이터 출력
            if data['response']['header']['resultCode'] == '00':
                items = data['response']['body']['items']['item']

                temperatures = []
                humidities = []
                wind_speeds = []
                weather_description = []

                for item in items:
                    category = item['category']
                    if category == 'TMP':  # 기온
                        temperatures.append(float(item['fcstValue']))
                    elif category == 'REH':  # 습도
                        humidities.append(float(item['fcstValue']))
                    elif category == 'WSD':  # 풍속
                        wind_speeds.append(float(item['fcstValue']))
                    elif category == 'PTY':  # 강수형태
                        weather_description.append(item['fcstValue'])
                    print(item)  # 각 예보 데이터 출력

                avg_temp = round(sum(temperatures) / len(temperatures), 1) if temperatures else None
                avg_humidity = round(sum(humidities) / len(humidities), 1) if humidities else None
                avg_wind_speed = round(sum(wind_speeds) / len(wind_speeds), 1) if wind_speeds else None

                # 평균 기상 상태 결정
                if '1' in weather_description or '2' in weather_description:
                    avg_weather = '비'
                elif '3' in weather_description:
                    avg_weather = '눈'
                elif avg_humidity > 70:
                    avg_weather = '구름 많음'
                else:
                    avg_weather = '맑음'

                weather_info = {
                    "average_temperature": avg_temp,
                    "average_weather": avg_weather,
                    "average_humidity": avg_humidity,
                    "average_wind_speed": avg_wind_speed
                }
                return weather_info
            else:
                print(f"Error: {data['response']['header']['resultMsg']}")
                return None
        except requests.exceptions.JSONDecodeError as e:
            print(f"JSON decoding failed: {e} - Response Text: {response.text}")
            return None
    else:
        print(f"HTTP error {response.status_code}")
        return None


# 옷 추천
@app.route('/clothes_propose')
def clothes_propose():
    return 'Hello clothes propose!'





# 옷 추가
@app.route('/upload', methods=['POST'])
def upload_image():
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
@app.route('/clothes/<uid>', methods=['GET'])
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
@app.route('/closet/delete/<uid>/<cloth_id>', methods=['DELETE'])
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