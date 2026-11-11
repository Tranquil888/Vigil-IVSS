"""SQLite schema. SQLAlchemy Core, no ORM, WAL, foreign keys on."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    event as sa_event,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine

SCHEMA_VERSION = "1"

EXPECTED_TABLES = frozenset(
    {
        "schema_meta",
        "camera",
        "person",
        "person_image",
        "embedding",
        "tracklet",
        "event",
        "snapshot",
        "unknown_cluster",
        "notification",
    }
)

metadata = MetaData()

schema_meta = Table(
    "schema_meta",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("value", String(255), nullable=False),
)

camera = Table(
    "camera",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(128), nullable=False),
    Column("created_at", Float, nullable=False),
)

person = Table(
    "person",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(128), nullable=False),
    Column("notes", Text, nullable=True),
    Column("enabled", Integer, nullable=False, default=1),
    Column("created_at", Float, nullable=False),
    Column("updated_at", Float, nullable=False),
)

person_image = Table(
    "person_image",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("person_id", Integer, ForeignKey("person.id", ondelete="CASCADE"), nullable=False),
    Column("path", Text, nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("quality", Float, nullable=False, default=0.0),
    Column("added_at", Float, nullable=False),
    Index("ix_person_image_person", "person_id"),
    Index("ix_person_image_sha", "sha256"),
)

embedding = Table(
    "embedding",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("person_id", Integer, ForeignKey("person.id", ondelete="CASCADE"), nullable=False),
    Column(
        "person_image_id",
        Integer,
        ForeignKey("person_image.id", ondelete="CASCADE"),
        nullable=True,
    ),
    Column("model_id", String(64), nullable=False),
    Column("model_version", String(64), nullable=False, default="1"),
    Column("dim", Integer, nullable=False),
    Column("vector", LargeBinary, nullable=False),
    Index("ix_embedding_person_model", "person_id", "model_id"),
)

tracklet = Table(
    "tracklet",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("camera_id", String(64), nullable=False),
    Column("started_at", Float, nullable=False),
    Column("ended_at", Float, nullable=True),
    Column("decision", String(32), nullable=False),
    Column("person_id", Integer, ForeignKey("person.id", ondelete="SET NULL"), nullable=True),
    Column("agg_score", Float, nullable=True),
    Column("n_obs", Integer, nullable=False, default=0),
    Index("ix_tracklet_camera_ts", "camera_id", "started_at"),
)

snapshot = Table(
    "snapshot",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("path", Text, nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("width", Integer, nullable=False),
    Column("height", Integer, nullable=False),
    Column("created_at", Float, nullable=False),
)

unknown_cluster = Table(
    "unknown_cluster",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("first_seen", Float, nullable=False),
    Column("last_seen", Float, nullable=False),
    Column("n_visits", Integer, nullable=False, default=1),
    Column("centroid", LargeBinary, nullable=False),
    Column("model_id", String(64), nullable=False),
    Index("ix_unknown_cluster_last_seen", "last_seen"),
)

event = Table(
    "event",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ts_start", Float, nullable=False),
    Column("ts_end", Float, nullable=True),
    Column("camera_id", String(64), nullable=False),
    Column("type", String(32), nullable=False),
    Column("zone", String(64), nullable=True),
    Column("person_id", Integer, ForeignKey("person.id", ondelete="SET NULL"), nullable=True),
    Column(
        "tracklet_id",
        Integer,
        ForeignKey("tracklet.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column(
        "unknown_cluster_id",
        Integer,
        ForeignKey("unknown_cluster.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("score", Float, nullable=True),
    Column(
        "snapshot_id",
        Integer,
        ForeignKey("snapshot.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("dedupe_key", String(128), nullable=True),
    Index("ix_event_ts_start", "ts_start"),
    Index("ix_event_camera_ts", "camera_id", "ts_start"),
    Index("ix_event_type_ts", "type", "ts_start"),
    Index("ix_event_dedupe", "dedupe_key", unique=True),
)

notification = Table(
    "notification",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("event_id", Integer, ForeignKey("event.id", ondelete="SET NULL"), nullable=True),
    Column("channel", String(32), nullable=False),
    Column("status", String(32), nullable=False),
    Column("reason", String(64), nullable=True),
    Column("created_at", Float, nullable=False),
    Index("ix_notification_created", "created_at"),
)


def make_engine(path: Union[str, Path]) -> Engine:
    engine = create_engine(
        "sqlite:///%s" % str(path),
        future=True,
        connect_args={"timeout": 10},
    )

    @sa_event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

    return engine


def create_schema(engine: Engine) -> Engine:
    Path(engine.url.database).parent.mkdir(parents=True, exist_ok=True)
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            sqlite_insert(schema_meta)
            .values(key="schema_version", value=SCHEMA_VERSION)
            .on_conflict_do_nothing(index_elements=["key"])
        )
    return engine
