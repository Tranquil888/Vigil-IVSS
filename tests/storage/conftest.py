import pytest
from sqlalchemy.engine import Engine

from vigil.storage.schema import create_schema, make_engine, person


def seed_person(engine: Engine, person_id: int, name: str = "Person") -> None:
    with engine.begin() as conn:
        conn.execute(
            person.insert().values(
                id=person_id,
                name=name,
                notes=None,
                enabled=1,
                created_at=0.0,
                updated_at=0.0,
            )
        )


@pytest.fixture()
def engine(tmp_path):
    return create_schema(make_engine(tmp_path / "vigil.db"))
