import pytest

from app.db import connect, init_db


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "test.sqlite3"
    init_db(path)
    return path


@pytest.fixture()
def conn(db_path):
    c = connect(db_path)
    yield c
    c.close()
