import pandas as pd
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, storage
import re
import logging as log
import top_bottom_chg
import weather_api
from clothes_detector import detector
import os
import requests
from datetime import datetime, timedelta
import urllib.parse
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


@app.route('/weather/get', methods=['GET'])
def weather():
    lat = float(request.args.get('lat'))
    lon = float(request.args.get('lon'))

    if not lat or not lon:
        return jsonify({'error': 'Latitude and Longitude are required'}), 400

    try:
        nx, ny, region_1, region_2, region_3 = weather_api.find_closest_region(lat, lon)
        log.info(f"Converted lat/lon to grid coordinates: nx={nx}, ny={ny}")
    except TypeError:
        return jsonify({'error': 'Failed to convert lat/lon to grid coordinates'}), 500

    if nx is None or ny is None:
        return jsonify({'error': 'Failed to convert lat/lon to grid coordinates'}), 500

    weather_info = weather_api.get_current_weather_info(nx, ny, region_1, region_2, region_3)

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
        nx, ny, region_1, region_2, region_3 = weather_api.find_closest_region(lat, lon)

        current_weather_info = weather_api.get_current_weather_info(nx, ny, region_1, region_2, region_3)

        if current_weather_info is None:
            return jsonify({'error': 'Failed to retrieve current weather information'}), 500

        temperatures = current_weather_info['currentTemp']
        weather = current_weather_info['weather']
        humidity = current_weather_info['humidity']
        wind_speed = current_weather_info['windSpeed']

        selected_info = (
            cloth_color, cloth_print, cloth_material, cloth_length, cloth_category
        ) if recommend_select in [1, 2] else None

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
            if success:
                top_color, top_print, top_material, top_length, top_category, top_id = top_clothes
                doc_ref = db.collection('users').document(uid).collection('closet').document(top_id)
                doc = doc_ref.get()

                response_data = jsonify(doc.to_dict()), 200
            else:
                response_data = jsonify({}), 200
        elif recommend_select == 2:  # 하의 추천
            success, bottom_clothes = result
            if success:
                bottom_color, bottom_print, bottom_material, bottom_length, bottom_category, bottom_id = bottom_clothes
                doc_ref = db.collection('users').document(uid).collection('closet').document(bottom_id)
                doc = doc_ref.get()

                response_data = jsonify(doc.to_dict()), 200
            else:
                response_data = jsonify({}), 200

        return response_data
    except Exception as e:
        log.error(f"예외 발생: {e}")
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

