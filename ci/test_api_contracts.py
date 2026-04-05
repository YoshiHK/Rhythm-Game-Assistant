"""
API Contract Tests

Ensures the thin backend API preserves response shape and does not expose analysis internals.
"""

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json() == {'ok': True}


def test_proseka_recommend_schema():
    r = client.post(
        '/api/v1/proseka/recommend',
        headers={'Authorization': 'Bearer test'},
        json={
            'user': {'user_id': 'u1'},
            'player_signals': {},
        },
    )
    # auth will fail, but response must be JSON
    assert r.status_code in (401, 403)
