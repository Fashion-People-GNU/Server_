from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore, storage
import re
from clothes_detector import detector
import os

cred = credentials.Certificate("flask-server/firebase/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

app = Flask(__name__)

UPLOAD_FOLDER = "clothes_detector/dataset/"


# 루트
@app.route('/')
def hello_world():
    return 'Hello World!'


# 옷 추천
@app.route('/clothes_propose')
def propose_cloth():
    return 'clothes_propose'


# 옷 추가
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file found'}), 400

    uid = request.form.get('uid')
    image_file = request.files.get('image')
    image_name = request.form.get('imageName')
    cloth_name = None

    if image_file.filename == '':
        return jsonify({'error': 'No image file name'}), 400

    # 파일 저장
    if image_file:
        file_path = os.path.join(UPLOAD_FOLDER)
        image_file.save(file_path)

    uid = re.sub(r"[^\uAC00-\uD7A30-9a-zA-Z\s]", "", uid)

    print(f"uid = {uid}")
    print(f"image file = {image_file}")
    print(f"image name = {image_name}")

    # 모듈 실행
    opt = detector.parse_opt()
    result = detector.main(opt)
    keys = result.keys()
    for i in keys:
        if str(i).find(uid) != -1:
            cloth_name = str(i).replace(uid, '')

    if cloth_name is None:
        return jsonify({'error': 'module execution failed'}), 500
    
    # 이미지를 Google Cloud Storage에 업로드
    bucket = storage.bucket('todays-clothes-1100f.appspot.com')
    blob = bucket.blob(f'images/{uid}/{image_name}')
    blob.upload_from_file(image_file)

    # 이미지 URL 생성
    image_url = blob.public_url

    # Firestore에 이미지 URL과 기타 정보 저장
    db = firestore.client()
    doc_ref = db.collection('users').document(uid).collection('closet').document(cloth_name)
    doc_ref.set({
        'imageUrl': image_url,
        'imageName': image_name
    })

    response_data = {
        'message': 'Data received successfully',
        'uid': uid,
        'image_name': image_name
    }

    return jsonify(response_data), 200


# 옷장 가져오기
@app.route("/getCloset", methods=['GET'])
def get_closet():
    uid = request.form.get('uid')


if __name__ == '__main__':
    app.run(host='0.0.0.0')
