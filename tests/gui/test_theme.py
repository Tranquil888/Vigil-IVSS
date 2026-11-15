import re
from pathlib import Path

import pytest

from vigil.gui.theme import (
    PALETTES,
    TEXT_PAIRS,
    build_theme,
    contrast_ratio,
)


def _rgb(hex_color: str):
    text = hex_color.lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


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


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_every_corner_is_square(scheme):
    qss = build_theme(scheme)
    for value in re.findall(r"border-radius:\s*([^;]+);", qss):
        assert value.strip() in ("0", "0px"), "rounded corner %r in %s" % (
            value.strip(),
            scheme,
        )
    assert "drawRoundedRect" not in qss


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_no_shadows_or_gradients(scheme):
    qss = build_theme(scheme)
    for banned in ("box-shadow", "drop-shadow", "qlineargradient", "qradialgradient"):
        assert banned not in qss.lower()


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_palette_is_grayscale_plus_green_and_red(scheme):
    colors = PALETTES[scheme]
    for token in ("bg", "panel", "panel_alt", "line", "text", "muted"):
        red, green, blue = _rgb(colors[token])
        assert max(red, green, blue) - min(red, green, blue) <= 16, (
            "%s is not neutral in %s" % (token, scheme)
        )
    for token in ("accent", "accent_fill"):
        red, green, blue = _rgb(colors[token])
        assert green > red and green > blue, "%s is not green in %s" % (token, scheme)
    for token in ("warn", "danger"):
        red, green, blue = _rgb(colors[token])
        assert red > green and red > blue, "%s is not red in %s" % (token, scheme)


@pytest.mark.parametrize("scheme", ["dark", "light"])
def test_no_blue_or_purple_tokens(scheme):
    for token, value in PALETTES[scheme].items():
        red, green, blue = _rgb(value)
        assert not (blue > red + 8 and blue > green + 8), (
            "%s uses a blue or purple tone in %s" % (token, scheme)
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
