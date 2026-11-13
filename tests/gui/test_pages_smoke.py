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
