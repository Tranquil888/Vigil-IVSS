import pytest

from tests.gui.fakes import FakeContext
from vigil.config.models import CameraConfig, VigilConfig
from vigil.gui.shell import MainWindow


@pytest.fixture
def window(qapp, tmp_path):
    config = VigilConfig(
        cameras=[CameraConfig(id="front", name="Front door", source="0")]
    )
    context = FakeContext(config)
    built = MainWindow(context, config, config_path=tmp_path / "config.toml")
    yield built
    built._quitting = True
    built.close()


def test_every_page_reaches_empty_loading_and_error(window):
    for page in window.pages:
        page.show_empty()
        assert page.view.mode == "empty", page.title
        page.show_loading()
        assert page.view.mode == "loading", page.title
        page.show_error("something failed")
        assert page.view.mode == "error", page.title
        page.show_content()
        assert page.view.mode == "content", page.title


def test_cameras_page_lists_the_configured_camera(window):
    page = window.cameras_page
    assert page.list_widget.count() == 1
    assert page.list_widget.item(0).text().startswith("Front door")


def test_events_page_lists_a_row(window):
    page = window.events_page
    assert page.table.rowCount() == 1
    assert page.table.item(0, 1).text() == "front"


def test_people_page_lists_a_person(window):
    page = window.people_page
    assert page.list_widget.count() == 1
    assert page.list_widget.item(0).text() == "Ann"


def test_live_page_builds_a_tile_per_camera(window):
    page = window.live_page
    assert list(page.tiles) == ["front"]
    assert page.view.mode == "content"


def test_settings_page_has_a_reset_row_and_advanced_toggle(window):
    page = window.settings_page
    assert page.rows
    page.advanced_box.setChecked(True)
    assert any(row.advanced and not row.isHidden() for row in page.rows)
    page.advanced_box.setChecked(False)
    assert page.view.mode == "content"


def test_page_feedback_reaches_the_status_bar(window):
    page = window.people_page

    page.report_action("Saved.", "warning")

    assert page.feedback.text() == "Saved."
    assert not page.feedback.isHidden()
    assert window.statusBar().currentMessage() == "Saved."


def test_cameras_page_keeps_a_multiline_source(window):
    page = window.cameras_page

    page.source_field.set_value("C:\\clips\\one.mp4\nC:\\clips\\two.mp4")

    assert page.source_field.value().splitlines() == [
        "C:\\clips\\one.mp4",
        "C:\\clips\\two.mp4",
    ]


def test_people_page_imports_several_photos_at_once(
    window, monkeypatch, tmp_path
):
    page = window.people_page
    paths = []
    for name in ("one.jpg", "two.jpg", "three.jpg"):
        path = tmp_path / name
        path.write_bytes(b"photo")
        paths.append(str(path))

    class Dialog:
        @staticmethod
        def getOpenFileNames(*args, **kwargs):
            return paths, "Images"

    monkeypatch.setattr("vigil.gui.pages.people.QFileDialog", Dialog)
    seen = []

    def record(person_id, path):
        seen.append(path.name)
        return True, "Photo saved."

    window.context.add_person_photo = record

    page.import_photo()

    assert seen == ["one.jpg", "two.jpg", "three.jpg"]
    assert page.feedback.text() == "Imported 3 photo(s)."


def test_people_page_reports_a_failed_photo(window, monkeypatch, tmp_path):
    page = window.people_page
    good = tmp_path / "good.jpg"
    bad = tmp_path / "bad.jpg"
    good.write_bytes(b"photo")
    bad.write_bytes(b"photo")

    class Dialog:
        @staticmethod
        def getOpenFileNames(*args, **kwargs):
            return [str(good), str(bad)], "Images"

    monkeypatch.setattr("vigil.gui.pages.people.QFileDialog", Dialog)

    def record(person_id, path):
        if path.name == "bad.jpg":
            return False, "no face found"
        return True, "Photo saved."

    window.context.add_person_photo = record

    page.import_photo()

    assert page.feedback.text() == (
        "Imported 1 photo(s), 0 already on file. 1 failed. bad.jpg: no face found"
    )
    assert page.feedback.objectName() == "FeedbackError"
