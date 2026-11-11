from vigil.app import main


def test_main_reports_a_broken_config_without_starting_qt(tmp_path, monkeypatch, capsys):
    broken = tmp_path / "config.toml"
    broken.write_text("this is not = valid toml", encoding="utf-8")
    monkeypatch.setenv("VIGIL_CONFIG", str(broken))

    code = main([])

    assert code == 2
    assert "not valid TOML" in capsys.readouterr().err
