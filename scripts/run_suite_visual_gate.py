from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

VIEWPORTS = ((1440, 900), (1366, 768), (390, 844))
DARK_VIEWPORT = (1440, 900)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render and validate the InfoClar Suite visual alignment gate.")
    parser.add_argument("--browser", required=True, help="Path to an installed Chromium-compatible browser")
    parser.add_argument("--macro-url", required=True)
    parser.add_argument("--world3-url", required=True)
    parser.add_argument("--output", default="visual-qa")
    return parser.parse_args()


def wait_for_product(page) -> None:
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2500)


def capture(page, url: str, output: Path) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    wait_for_product(page)
    page.screenshot(path=str(output), full_page=False)


def audit_macro(page, url: str, width: int, height: int) -> dict:
    separator = "&" if "?" in url else "?"
    page.goto(f"{url}{separator}visual-audit=1", wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_selector("#visual-audit-result", state="attached", timeout=15_000)
    result = json.loads(page.locator("#visual-audit-result").text_content())
    expected = [width, height]
    if result["viewport"] != expected:
        raise SystemExit(f"Exact viewport gate failed: expected {expected}, browser reported {result['viewport']}")
    if result["horizontalOverflow"]:
        raise SystemExit(f"Horizontal page overflow at {width}x{height}")
    if result["panelOverlaps"]:
        raise SystemExit(f"Panel overlap at {width}x{height}: {result['panelOverlaps']}")
    if result["smallControls"]:
        raise SystemExit(f"Controls below 34px at {width}x{height}: {result['smallControls']}")
    return result


def rgb(hex_value: str) -> tuple[float, float, float]:
    value = hex_value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def relative_luminance(hex_value: str) -> float:
    channels = []
    for channel in rgb(hex_value):
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def validate_canonical_contrast() -> dict[str, float]:
    checks = {
        "light_text_on_surface": contrast_ratio("#28313d", "#ffffff"),
        "light_muted_on_surface": contrast_ratio("#687384", "#ffffff"),
        "light_muted_on_surface_muted": contrast_ratio("#687384", "#f8f9fb"),
        "dark_text_on_surface": contrast_ratio("#e7ebf0", "#20242b"),
        "dark_muted_on_surface": contrast_ratio("#a4adba", "#20242b"),
    }
    failing = {name: ratio for name, ratio in checks.items() if ratio < 4.5}
    if failing:
        raise SystemExit(f"Canonical text contrast below WCAG AA 4.5:1: {failing}")
    return checks


def side_by_side(left_path: Path, right_path: Path, output: Path, label: str) -> None:
    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB")
    if left.size != right.size:
        raise SystemExit(f"Comparison images must have equal dimensions: {left.size} vs {right.size}")
    canvas = Image.new("RGB", (left.width * 2, left.height + 34), "white")
    canvas.paste(left, (0, 34))
    canvas.paste(right, (left.width, 34))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 10), f"WORLD3 — canonical | {label}", fill="black")
    draw.text((left.width + 12, 10), f"MACRO — aligned | {label}", fill="black")
    canvas.save(output)


def main() -> None:
    args = parse_args()
    root = Path(args.output)
    macro_dir = root / "macro"
    world3_dir = root / "world3"
    comparison_dir = root / "side-by-side"
    audit_dir = root / "audit"
    for directory in (macro_dir, world3_dir, comparison_dir, audit_dir):
        directory.mkdir(parents=True, exist_ok=True)

    report: dict[str, object] = {
        "gate": "Suite Visual Alignment Gate",
        "canonical_product": "World3 Empirical",
        "candidate_product": "Romania Macro-Financial Dynamics",
        "exact_viewports": {},
        "contrast": validate_canonical_contrast(),
        "focus_ring": "0 0 0 3px rgba(93, 95, 239, 0.32)",
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=args.browser,
            headless=True,
            args=["--no-sandbox", "--disable-gpu"],
        )
        try:
            for width, height in VIEWPORTS:
                label = f"{width}x{height}"
                macro_path = macro_dir / f"{label}.png"
                world3_path = world3_dir / f"{label}.png"

                macro_context = browser.new_context(
                    viewport={"width": width, "height": height},
                    color_scheme="light",
                    device_scale_factor=1,
                )
                macro_page = macro_context.new_page()
                capture(macro_page, args.macro_url, macro_path)
                audit = audit_macro(macro_page, args.macro_url, width, height)
                macro_context.close()

                world_context = browser.new_context(
                    viewport={"width": width, "height": height},
                    color_scheme="light",
                    device_scale_factor=1,
                )
                world_page = world_context.new_page()
                capture(world_page, args.world3_url, world3_path)
                world_context.close()

                side_by_side(world3_path, macro_path, comparison_dir / f"{label}.png", label)
                report["exact_viewports"][label] = audit

            width, height = DARK_VIEWPORT
            label = f"{width}x{height}-dark"
            macro_path = macro_dir / f"{label}.png"
            world3_path = world3_dir / f"{label}.png"

            macro_context = browser.new_context(
                viewport={"width": width, "height": height},
                color_scheme="dark",
                device_scale_factor=1,
            )
            macro_page = macro_context.new_page()
            capture(macro_page, args.macro_url, macro_path)
            macro_context.close()

            world_context = browser.new_context(
                viewport={"width": width, "height": height},
                color_scheme="dark",
                device_scale_factor=1,
            )
            world_page = world_context.new_page()
            capture(world_page, args.world3_url, world3_path)
            world_context.close()

            side_by_side(world3_path, macro_path, comparison_dir / f"{label}.png", label)
        finally:
            browser.close()

    (audit_dir / "visual-gate-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
