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


# 옷 추천
@app.route('/clothes_propose')
def propose_cloth():
    weather_info = get_weather_info()

    if weather_info is None:
        return jsonify({'error': 'Failed to retrieve weather information'}), 500

    # 날씨 정보를 JSON 형태로 반환
    print(weather_info)

    return str(weather_info)


def get_weather_info():
    url = "https://www.weather.go.kr/weather/observation/currentweather.jsp"  # 경남 진주 날씨 정보 URL
    response = requests.get(url)
    response.encoding = 'utf-8'

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', id='weather_table')

    if table is None:
        return jsonify({'error': 'Not Found Table'}), 404

    for row in table.tbody.find_all('tr'):
        if row.th.text.strip() == '진주':
            return row


# 옷 추가
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file found'}), 400
    uid = request.form.get('uid')
    image_file = request.files.get('image')
    image_name = request.form.get('imageName').replace("\"", "")
    cloth_name = None

    if image_file.filename == '':
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
                'style': style
            })

    response_data = {
        'message': 'Data received successfully',
        'uid': uid,
        'image_name': image_name
    }
    log.info(str(response_data))
    return jsonify(response_data), 200


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
