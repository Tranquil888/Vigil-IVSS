from vigil.app import main, should_show_window


def test_main_reports_a_broken_config_without_starting_qt(tmp_path, monkeypatch, capsys):
    broken = tmp_path / "config.toml"
    broken.write_text("this is not = valid toml", encoding="utf-8")
    monkeypatch.setenv("VIGIL_CONFIG", str(broken))

    code = main([])

    assert code == 2
    assert "not valid TOML" in capsys.readouterr().err


def test_default_start_shows_the_window():
    assert should_show_window(False, console_attached=False, tray_available=True)


def test_console_launch_shows_the_window_even_when_minimized_is_saved():
    # A terminal launch is an explicit request to see the app. Starting
    # hidden here looks like the app failed to launch.
    assert should_show_window(True, console_attached=True, tray_available=True)


def test_background_launch_uses_the_tray_when_it_exists():
    assert not should_show_window(True, console_attached=False, tray_available=True)


def test_background_launch_shows_the_window_without_a_tray():
    # With no tray there is no way to restore a hidden window.
    assert should_show_window(True, console_attached=False, tray_available=False)
