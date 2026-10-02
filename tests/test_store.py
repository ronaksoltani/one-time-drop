from one_time_drop.store import DropStore


def test_token_is_consumed_once(tmp_path):
    store = DropStore(tmp_path)
    path = tmp_path / "blob"
    path.write_bytes(b"private")
    store.create("random-token", path, "report.txt", 60)
    assert store.consume("random-token").filename == "report.txt"
    assert store.consume("random-token") is None


def test_expired_token_is_removed(tmp_path):
    store = DropStore(tmp_path)
    path = tmp_path / "old"
    path.write_bytes(b"expired")
    store.create("old-token", path, "old.txt", -1)
    assert store.consume("old-token") is None
    assert not path.exists()
