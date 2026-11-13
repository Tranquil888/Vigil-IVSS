import threading
from types import SimpleNamespace

from tests.gui.fakes import FakeContext
from vigil.config.models import CameraConfig, VigilConfig
from vigil.gui.shell import NAV, MainWindow


def build_window(tmp_path):
    config = VigilConfig(
        cameras=[CameraConfig(id="front", name="Front door", source="0")]
    )
    context = FakeContext(config)
    window = MainWindow(context, config, config_path=tmp_path / "config.toml")
    return window, context


def test_window_has_exactly_five_destinations(qapp, tmp_path):
    window, _context = build_window(tmp_path)
    assert len(NAV) == 5
    assert len(window.nav_buttons) == 5
    assert len(window.pages) == 5
    assert [button.text() for button in window.nav_buttons] == [
        "Cameras",
        "Live",
        "Events",
        "People",
        "Settings",
    ]
    window._quitting = True
    window.close()


def test_each_navigation_button_switches_the_stack(qapp, tmp_path):
    window, _context = build_window(tmp_path)
    for index, button in enumerate(window.nav_buttons):
        button.click()
        assert window.stack.currentIndex() == index
        assert window.current_page() is window.pages[index]
    window._quitting = True
    window.close()


def test_window_starts_on_live(qapp, tmp_path):
    window, _context = build_window(tmp_path)
    assert window.stack.currentIndex() == 1
    assert window.nav_buttons[1].isChecked()
    window._quitting = True
    window.close()


def test_theme_switch_updates_the_stylesheet(qapp, tmp_path):
    window, _context = build_window(tmp_path)
    window.apply_scheme("light")
    assert window.scheme == "light"
    assert "#F4F5F3" in window.styleSheet()
    window.apply_scheme("dark")
    assert "#12161A" in window.styleSheet()
    window._quitting = True
    window.close()


def test_notification_reaches_the_status_bar(qapp, tmp_path):
    window, _context = build_window(tmp_path)
    window.notify("Vigil: Ann", "Ann was recognised at Front door.")
    assert "Ann was recognised" in window.statusBar().currentMessage()
    window._quitting = True
    window.close()


def test_notification_from_a_worker_thread_is_queued(qapp, tmp_path):
    window, _context = build_window(tmp_path)

    worker = threading.Thread(
        target=window.notify, args=("Vigil: Ann", "Ann was recognised.")
    )
    worker.start()
    worker.join()
    qapp.processEvents()

    assert "Ann was recognised" in window.statusBar().currentMessage()
    window._quitting = True
    window.close()


def test_status_bar_warns_when_recognition_is_disabled(qapp, tmp_path):
    window, context = build_window(tmp_path)
    context.status = SimpleNamespace(
        available=True,
        cuda=False,
        detector="dlib_cnn",
        reason=(
            "recognition is disabled, missing "
            "shape_predictor_68_face_landmarks.dat"
        ),
    )

    window._update_status()

    assert "recognition is disabled" in window.backend_label.text()
    assert window.backend_label.objectName() == "Warning"
    window._quitting = True
    window.close()
