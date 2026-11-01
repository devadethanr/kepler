from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from memory.models import CognitionRunRow, CognitionReportRow
from research_room.store import Store


@pytest.fixture
def store(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "rooms.db"))
    CognitionRunRow.__table__.create(engine)
    CognitionReportRow.__table__.create(engine)

    @contextmanager
    def scope():
        with Session(engine, expire_on_commit=False) as session:
            with session.begin():
                yield session

    yield Store(scope)
    engine.dispose()
