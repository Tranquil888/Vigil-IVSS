import pytest
from sqlalchemy import inspect

from vigil.storage.schema import EXPECTED_TABLES, create_schema, make_engine


@pytest.fixture()
def engine(tmp_path):
    eng = make_engine(tmp_path / "vigil.db")
    create_schema(eng)
    return eng


def test_schema_creates_every_table(engine):
    names = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES.issubset(names)


def test_schema_is_idempotent(engine):
    create_schema(engine)
    create_schema(engine)
    assert "event" in inspect(engine).get_table_names()


def test_event_indexes_exist(engine):
    names = {index["name"] for index in inspect(engine).get_indexes("event")}
    assert "ix_event_ts_start" in names
    assert "ix_event_camera_ts" in names
    assert "ix_event_type_ts" in names
    assert "ix_event_dedupe" in names


def test_foreign_keys_are_on(engine):
    with engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_journal_mode_is_wal(engine):
    with engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA journal_mode").scalar().lower() == "wal"
