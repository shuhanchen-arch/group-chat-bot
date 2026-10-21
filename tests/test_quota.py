from src.plugins.aichat.quota import QuotaStore


def test_limit_and_refund(tmp_path):
    q = QuotaStore(str(tmp_path / "q.db"))
    assert all(q.try_consume("1", "flash", 10) for _ in range(10))
    assert not q.try_consume("1", "flash", 10)
    assert q.used("1", "flash") == 10
    # 其他人、其他类型互不影响
    assert q.try_consume("2", "flash", 10)
    assert q.try_consume("1", "image", 10)
    q.refund("1", "flash")
    assert q.try_consume("1", "flash", 10)
    assert not q.try_consume("1", "flash", 10)


def test_unlimited(tmp_path):
    q = QuotaStore(str(tmp_path / "q.db"))
    assert all(q.try_consume("1", "image", 0) for _ in range(50))
    assert q.used("1", "image") == 0


def test_persists(tmp_path):
    path = str(tmp_path / "q.db")
    QuotaStore(path).try_consume("1", "flash", 10)
    assert QuotaStore(path).used("1", "flash") == 1


def test_new_day_resets(tmp_path, monkeypatch):
    q = QuotaStore(str(tmp_path / "q.db"))
    monkeypatch.setattr(q, "today", lambda: "2026-10-20")
    for _ in range(10):
        q.try_consume("1", "flash", 10)
    monkeypatch.setattr(q, "today", lambda: "2026-10-21")
    assert q.try_consume("1", "flash", 10)
