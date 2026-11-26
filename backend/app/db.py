import json

import firebase_admin
from firebase_admin import credentials, firestore

from app import config

_client = None


def get_db():
    """Firestore 클라이언트(지연 초기화). 키는 환경변수에서만 읽는다."""
    global _client
    if _client is None:
        if config.FIREBASE_SERVICE_ACCOUNT_JSON:
            cred = credentials.Certificate(json.loads(config.FIREBASE_SERVICE_ACCOUNT_JSON))
        elif config.FIREBASE_SERVICE_ACCOUNT_PATH:
            cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_PATH)
        else:
            raise RuntimeError(
                "FIREBASE_SERVICE_ACCOUNT_JSON 또는 FIREBASE_SERVICE_ACCOUNT_PATH 를 설정하세요."
            )
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        _client = firestore.client()
    return _client
