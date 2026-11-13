"""Small stand-ins for AppContext, used only by the GUI tests."""

from __future__ import annotations

import time

from vigil.analysis.pipeline import OverlayStore
from vigil.config.models import CameraConfig, VigilConfig
from vigil.core.queues import LatestFrame
from vigil.video.state import CameraState


class FakeStatus:
    available = True
    cuda = False
    detector = "dlib_hog"
    reason = "test"


class FakeManager:
    def __init__(self, camera_ids=("front",)):
        self.camera_ids = list(camera_ids)
        self._queues = {camera_id: LatestFrame() for camera_id in self.camera_ids}

    def display_queue(self, camera_id):
        return self._queues[camera_id]

    def state(self, camera_id):
        return CameraState.STREAMING


class FakePeopleStore:
    def __init__(self):
        self._rows = {1: {"id": 1, "name": "Ann", "notes": "", "enabled": 1}}
        self._next = 2
        self.images = {}

    def rows(self):
        return [dict(row) for row in self._rows.values()]

    def add(self, name, notes=None, enabled=True):
        person_id = self._next
        self._next += 1
        self._rows[person_id] = {
            "id": person_id,
            "name": name,
            "notes": notes or "",
            "enabled": 1 if enabled else 0,
        }
        return person_id

    def update(self, person_id, name, notes=None, enabled=True):
        self._rows[person_id] = {
            "id": person_id,
            "name": name,
            "notes": notes or "",
            "enabled": 1 if enabled else 0,
        }

    def delete(self, person_id):
        self._rows.pop(person_id, None)

    def count_images(self, person_id):
        return len(self.images.get(person_id, []))


class FakeReader:
    def __init__(self, store):
        self.store = store
        self._events = [
            {
                "id": 1,
                "ts_start": time.time() - 30,
                "ts_end": time.time() - 29,
                "camera_id": "front",
                "type": "stranger",
                "person_id": None,
                "unknown_cluster_id": 3,
                "score": 0.72,
                "snapshot_id": None,
            }
        ]

    def people(self):
        return self.store.rows()

    def events(self, limit=200, camera_id=None, event_type=None):
        rows = self._events
        if camera_id:
            rows = [row for row in rows if row["camera_id"] == camera_id]
        if event_type:
            rows = [row for row in rows if row["type"] == event_type]
        return rows[:limit]

    def person_images(self, person_id):
        return self.store.images.get(person_id, [])

    def snapshots(self, limit=50):
        return []


class FakeContext:
    def __init__(self, config=None):
        self.config = config or VigilConfig(
            cameras=[CameraConfig(id="front", name="Front door", source="0")]
        )
        self.people_store = FakePeopleStore()
        self.reader = FakeReader(self.people_store)
        self.manager = FakeManager()
        self.overlays = OverlayStore()
        self.status = FakeStatus()
        self.names = {1: "Ann"}
        self.toast_callback = None

    def set_toast_callback(self, callback):
        self.toast_callback = callback

    def rebuild_gallery(self):
        return len(self.people_store.rows())

    def add_person_photo(self, person_id, path):
        return True, "Photo added."
