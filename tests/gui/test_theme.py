from pathlib import Path

import pytest

from vigil.gui.theme import (
    PALETTES,
    TEXT_PAIRS,
    build_theme,
    contrast_ratio,
)


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_every_palette_token_reaches_the_stylesheet(scheme):
    qss = build_theme(scheme)
    for token, value in PALETTES[scheme].items():
        assert value in qss, "%s is missing from the %s theme" % (token, scheme)


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_all_text_pairs_meet_wcag_aa(scheme):
    colors = PALETTES[scheme]
    for foreground, background in TEXT_PAIRS:
        ratio = contrast_ratio(colors[foreground], colors[background])
        assert ratio >= 4.5, "%s on %s is %.2f:1 in %s" % (
            foreground,
            background,
            ratio,
            scheme,
        )


def test_unknown_scheme_is_rejected():
    with pytest.raises(ValueError):
        build_theme("sepia")


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_check_indicator_has_a_real_image(scheme):
    qss = build_theme(scheme)
    assert "check-%s.png" % scheme in qss
    icon = Path(__file__).parents[2] / "src" / "vigil" / "gui" / "resources" / (
        "check-%s.png" % scheme
    )
    assert icon.is_file()
    assert icon.stat().st_size > 0
