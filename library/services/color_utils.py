import colorsys


def shade_hex_color(hex_color: str, lightness_delta: float) -> str:
    """
    Return a lighter or darker shade of a hex color, keeping its hue and saturation.

    param hex_color: A "#rrggbb" color string.
    param lightness_delta: How much to shift lightness by, in the range [-1, 1].
        Negative values darken the color, positive values lighten it.

    :return: A new "#rrggbb" color string.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(1.0, max(0.0, l + lightness_delta))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def contrast_shade(hex_color: str) -> str:
    """
    Return a shade of a hex color suitable as the second stop of a two-tone
    gradient with it: darker for light/vivid colors, lighter for already-dark ones.

    param hex_color: A "#rrggbb" color string.

    :return: A new "#rrggbb" color string, shifted enough to read as a distinct tone.
    """
    hex_color_clean = hex_color.lstrip("#")
    r, g, b = (int(hex_color_clean[i : i + 2], 16) / 255 for i in (0, 2, 4))
    _, lightness, _ = colorsys.rgb_to_hls(r, g, b)
    delta = -0.16 if lightness > 0.35 else 0.22
    return shade_hex_color(hex_color, delta)


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """
    Convert a hex color into a CSS rgba(...) string.

    param hex_color: A "#rrggbb" color string.
    param alpha: Opacity, in the range [0, 1].

    :return: A CSS "rgba(r, g, b, a)" string.
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"
