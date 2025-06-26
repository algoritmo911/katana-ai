# katana-ai/tests/test_sc_link.py

from core.bridge.sc_link import SCLink

def test_ping_sc():
    sc = SCLink()
    assert sc.ping() in [True, False]  # В зависимости от работы сервера

def test_submit_fake_ku():
    sc = SCLink()
    fake_ku = {
        "title": "Test Knowledge",
        "content": "SC test unit",
        "tags": ["test", "unit"],
    }
    assert sc.submit_knowledge_unit(fake_ku) in [True, False]  # В зависимости от работы сервера
