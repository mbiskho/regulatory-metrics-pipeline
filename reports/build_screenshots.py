"""Render dependency-free PNG/SVG report images from the bundled sample."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from regulatory_metrics_pipeline import calculate_metrics

OUT = Path(__file__).resolve().parent
NAVY = (23, 42, 69)
BLUE = (46, 112, 220)
TEAL = (31, 164, 151)
MUTED = (103, 119, 139)
GRID = (225, 232, 240)
PALE = (244, 248, 252)
WHITE = (255, 255, 255)
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    ",": ("00000", "00000", "00000", "00000", "00110", "00100", "01000"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
}


class Canvas:
    def __init__(self, width: int = 1200, height: int = 760):
        self.width, self.height = width, height
        self.pixels = bytearray(WHITE * (width * height))

    def rect(self, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
        for yy in range(max(0, y), min(self.height, y + h)):
            start = (yy * self.width + max(0, x)) * 3
            end = (yy * self.width + min(self.width, x + w)) * 3
            self.pixels[start:end] = bytes(color) * max(0, min(self.width, x + w) - max(0, x))

    def line(self, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int], thickness: int = 2) -> None:
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.rect(x0 - thickness // 2, y0 - thickness // 2, thickness, thickness, color)
            if x0 == x1 and y0 == y1:
                break
            twice = 2 * err
            if twice >= dy:
                err += dy
                x0 += sx
            if twice <= dx:
                err += dx
                y0 += sy

    def text(self, x: int, y: int, value: str, color: tuple[int, int, int] = NAVY, scale: int = 2) -> None:
        cursor = x
        for char in value.upper():
            glyph = FONT.get(char)
            if glyph:
                for row, bits in enumerate(glyph):
                    for column, bit in enumerate(bits):
                        if bit == "1":
                            self.rect(cursor + column * scale, y + row * scale, scale, scale, color)
            cursor += 6 * scale

    def save(self, path: Path) -> None:
        raw = b"".join(b"\0" + bytes(self.pixels[y * self.width * 3:(y + 1) * self.width * 3])
                       for y in range(self.height))
        def chunk(tag: bytes, payload: bytes) -> bytes:
            return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">2I5B", self.width, self.height, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
        path.write_bytes(png)


def svg_save(name: str, inner: str) -> None:
    template = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">
<rect width="1200" height="760" fill="#ffffff"/>
<style>text{{font-family:Arial,sans-serif;fill:#172a45}} .muted{{fill:#67778b}} .grid{{stroke:#e1e8f0;stroke-width:1}} .card{{fill:#f4f8fc;stroke:#e1e8f0}}</style>
{inner}</svg>'''
    (OUT / f"{name}.svg").write_text(template, encoding="utf-8")


def main() -> None:
    source = json.loads((ROOT / "examples/sample_metrics.json").read_text(encoding="utf-8"))
    result = calculate_metrics(source)
    metrics = result["metrics"]
    components = [
        ("CREDIT RWA", metrics["credit_risk_weighted_assets"]),
        ("OP RISK RWA", metrics["illustrative_operational_rwa"]),
        ("MARKET RWA", metrics["illustrative_market_rwa"]),
    ]
    capital_ratio = metrics["illustrative_total_capital_ratio"] * 100
    cards = [
        ("CAPITAL RATIO - ILLUSTRATIVE", f"{capital_ratio:.2f}%"),
        ("TOTAL RWA - ILLUSTRATIVE", f'{metrics["illustrative_total_risk_weighted_assets"]/1e6:.1f}M'),
        ("CAPITAL BUFFER - ILLUSTRATIVE", f'{metrics["illustrative_capital_buffer"]/1e6:.1f}M'),
    ]
    maximum = max(value for _, value in components) or 1

    canvas = Canvas()
    canvas.text(56, 38, "REGULATORY METRICS PIPELINE", NAVY, 4)
    canvas.text(58, 82, "SYNTHETIC DATA - ILLUSTRATIVE CAPITAL PROXIES ONLY", MUTED, 2)
    for i, (label, value) in enumerate(cards):
        x = 56 + i * 366
        canvas.rect(x, 126, 334, 104, PALE)
        canvas.text(x + 18, 145, label, MUTED, 1)
        canvas.text(x + 18, 178, value, BLUE if i == 0 else TEAL, 3)
    canvas.text(58, 277, "ILLUSTRATIVE RWA COMPONENTS", NAVY, 3)
    for index, (label, value) in enumerate(components):
        y = 350 + index * 83
        canvas.text(66, y, label, NAVY, 2)
        width = int(value / maximum * 680)
        canvas.rect(330, y - 5, max(width, 4), 28, BLUE if index == 0 else TEAL)
        canvas.text(330 + width + 18, y, f"{value/1e6:.1f}M", MUTED, 2)
    canvas.text(58, 642, "RWA = CREDIT RWA + FLAT CHARGES X 12.5", MUTED, 2)
    canvas.text(58, 695, "NOT A REGULATORY DETERMINATION OR COMPLIANCE CLAIM", MUTED, 2)
    canvas.save(OUT / "overview.png")

    metric_markup = "".join(
        f'<rect class="card" x="{56+i*366}" y="126" width="334" height="104" rx="14"/>'
        f'<text class="muted" x="{74+i*366}" y="158" font-size="13">{label}</text>'
        f'<text x="{74+i*366}" y="205" font-size="30" font-weight="700" fill="#2e70dc">{value}</text>'
        for i, (label, value) in enumerate(cards)
    )
    chart_markup = []
    for i, (label, value) in enumerate(components):
        y = 350 + i * 83
        width = value / maximum * 680
        chart_markup.append(
            f'<text x="66" y="{y+20}" font-size="15">{label}</text>'
            f'<rect x="330" y="{y-5}" width="{width:.1f}" height="28" rx="6" fill="{("#2e70dc" if i == 0 else "#1fa497")}"/>'
            f'<text class="muted" x="{350+width:.1f}" y="{y+16}" font-size="14">{value/1e6:.1f}M</text>'
        )
    svg_save("overview", f'''
<text x="56" y="76" font-size="34" font-weight="700">REGULATORY METRICS PIPELINE</text>
<text class="muted" x="58" y="106" font-size="16">SYNTHETIC DATA - ILLUSTRATIVE CAPITAL PROXIES ONLY</text>
{metric_markup}<text x="58" y="307" font-size="22" font-weight="700">ILLUSTRATIVE RWA COMPONENTS</text>
{''.join(chart_markup)}
<text class="muted" x="58" y="664" font-size="14">RWA = CREDIT RWA + FLAT CHARGES X 12.5</text>
<text class="muted" x="58" y="710" font-size="14">NOT A REGULATORY DETERMINATION OR COMPLIANCE CLAIM</text>''')

    flow = Canvas()
    flow.text(56, 38, "CAPITAL METRICS - PIPELINE FLOW", NAVY, 4)
    flow.text(58, 82, "VALIDATED INPUTS FEED SEPARATE CREDIT, OPERATIONAL AND MARKET PROXIES", MUTED, 2)
    stages = [("SYNTHETIC", "INPUTS"), ("VALIDATE", "RANGES / YEARS"), ("CALCULATE", "CHARGES / RWA"), ("REPORT", "RATIOS / BUFFER")]
    for i, (top, bottom) in enumerate(stages):
        x = 56 + i * 286
        flow.rect(x, 142, 224, 88, PALE)
        flow.text(x + 15, 159, top, BLUE, 2)
        flow.text(x + 15, 188, bottom, NAVY, 1)
        if i < len(stages) - 1:
            flow.line(x + 229, 185, x + 270, 185, TEAL, 3)
            flow.line(x + 261, 176, x + 270, 185, TEAL, 3)
            flow.line(x + 261, 194, x + 270, 185, TEAL, 3)
    flow.text(58, 280, "DATA-DRIVEN CONTRIBUTION TO ILLUSTRATIVE TOTAL RWA", NAVY, 3)
    for index, (label, value) in enumerate(components):
        y = 360 + index * 80
        flow.text(66, y, label, NAVY, 2)
        width = int(value / maximum * 680)
        flow.rect(330, y - 5, max(width, 4), 28, BLUE if index == 0 else TEAL)
        flow.text(330 + width + 18, y, f"{value/1e6:.1f}M", MUTED, 2)
    flow.text(58, 642, "CREDIT RWA + (OPERATIONAL CHARGE + MARKET CHARGE) X 12.5", MUTED, 2)
    flow.text(58, 695, "SIMPLIFIED SYNTHETIC MODEL - NOT COMPLIANCE ADVICE", MUTED, 2)
    flow.save(OUT / "flow.png")

    stage_svg = []
    for i, (top, bottom) in enumerate(stages):
        x = 56 + i * 286
        stage_svg.append(
            f'<rect class="card" x="{x}" y="142" width="224" height="88" rx="12"/>'
            f'<text x="{x+16}" y="177" font-size="18" font-weight="700">{top}</text>'
            f'<text class="muted" x="{x+16}" y="205" font-size="13">{bottom}</text>'
        )
        if i < len(stages) - 1:
            stage_svg.append(f'<path d="M{x+232} 186 H{x+267}" stroke="#1fa497" stroke-width="3" marker-end="url(#arrow)"/>')
    flow_chart = []
    for i, (label, value) in enumerate(components):
        y = 360 + i * 80
        width = value / maximum * 680
        flow_chart.append(
            f'<text x="66" y="{y+20}" font-size="15">{label}</text>'
            f'<rect x="330" y="{y-5}" width="{width:.1f}" height="28" rx="6" fill="{("#2e70dc" if i == 0 else "#1fa497")}"/>'
            f'<text class="muted" x="{350+width:.1f}" y="{y+16}" font-size="14">{value/1e6:.1f}M</text>'
        )
    svg_save("flow", f'''
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#1fa497"/></marker></defs>
<text x="56" y="76" font-size="34" font-weight="700">CAPITAL METRICS - PIPELINE FLOW</text>
<text class="muted" x="58" y="106" font-size="16">VALIDATED INPUTS FEED SEPARATE CREDIT, OPERATIONAL AND MARKET PROXIES</text>
{''.join(stage_svg)}<text x="58" y="307" font-size="22" font-weight="700">DATA-DRIVEN CONTRIBUTION TO ILLUSTRATIVE TOTAL RWA</text>
{''.join(flow_chart)}
<text class="muted" x="58" y="664" font-size="14">CREDIT RWA + (OPERATIONAL CHARGE + MARKET CHARGE) X 12.5</text>
<text class="muted" x="58" y="710" font-size="14">SIMPLIFIED SYNTHETIC MODEL - NOT COMPLIANCE ADVICE</text>''')


if __name__ == "__main__":
    main()
