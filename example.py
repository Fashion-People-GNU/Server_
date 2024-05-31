import firebase_admin
from firebase_admin import credentials, firestore, storage


cred = credentials.Certificate("flask-server/firebase/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

doc_ref = db.collection('users').document('ViUFCYEA6za0MaFlwDFGIKPscy82').collection('closet')
docs = doc_ref.get()

closet_data = []

for doc in docs:
    closet_data.append(doc.to_dict())

print(closet_data)
