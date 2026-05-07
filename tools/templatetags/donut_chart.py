from django import template
import math
from django.utils.html import format_html

register = template.Library()

RADIUS = 90
CIRCUMFERENCE = 2 * math.pi * RADIUS


@register.inclusion_tag("components/donut_chart.html")
def donut_chart(job: dict, label: str):
    # ✅ SAFE DICT ACCESS
    total = job.get("total_items", 0) or 0

    valid = job.get("valid_count", 0) or 0
    risky = job.get("risky_count", 0) or 0
    invalid = job.get("invalid_count", 0) or 0

    # ✅ DEFAULT UNKNOWN
    unknown = max(total - (valid + risky + invalid), 0)

    def length(value):
        return (value / total) * CIRCUMFERENCE if total else 0

    # Order matters (unknown first = base ring)
    segments = [
        ("valid", valid),
        ("risky", risky),
        ("invalid", invalid),
        ("unknown", unknown),
    ]

    dash = {}
    offset = 0

    for key, value in segments:
        seg_len = length(value)
        dash[key] = {
            "len": seg_len,
            "offset": -offset
        }
        offset += seg_len

    return {
        "total": total,
        "dash": dash,
        "circ": CIRCUMFERENCE,
        "percent": round((valid / total) * 100, 1) if total else 0,
        "label": label
    }

def full_ring(cx, cy, ro, ri):
    return (
        f"M {cx} {cy-ro} "
        f"A {ro} {ro} 0 1 1 {cx} {cy+ro} "
        f"A {ro} {ro} 0 1 1 {cx} {cy-ro} "
        f"M {cx} {cy-ri} "
        f"A {ri} {ri} 0 1 0 {cx} {cy+ri} "
        f"A {ri} {ri} 0 1 0 {cx} {cy-ri} Z"
    )

def polar(cx, cy, r, angle):
    angle = math.radians(angle - 90)
    return round(cx + r * math.cos(angle), 3), round(cy + r * math.sin(angle), 3)


def arc_path(cx, cy, ro, ri, start, end):
    x1, y1 = polar(cx, cy, ro, start)
    x2, y2 = polar(cx, cy, ro, end)
    x3, y3 = polar(cx, cy, ri, end)
    x4, y4 = polar(cx, cy, ri, start)

    large = 1 if (end - start) > 180 else 0

    return (
        f"M {x1} {y1} "
        f"A {ro} {ro} 0 {large} 1 {x2} {y2} "
        f"L {x3} {y3} "
        f"A {ri} {ri} 0 {large} 0 {x4} {y4} Z"
    )

@register.simple_tag
def build_overall_breakdown_svg(breakdown):
    cx = cy = 112
    ro, ri = 100, 80

    total = 0
    start = 0
    paths = []

    for _, value, color in breakdown["items"]:
        if value:
            total += value

    for _, value, color in breakdown["items"]:
        if value == 0 or total == 0:
            continue

        if value == total:
            d = full_ring(cx, cy, ro, ri)
        else:
            angle = (value / total) * 360
            d = arc_path(cx, cy, ro, ri, start, start + angle)
            start += angle

        paths.append(
            format_html('<path d="{}" fill="{}"></path>', d, color)
        )

    return format_html(
        """
        <svg width="224" height="224" viewBox="0 0 224 224">
            {}
            <text x="112" y="102" text-anchor="middle"
                  style="font-size:36px;font-weight:300;fill:#6b7280">{}</text>
            <text x="112" y="127" text-anchor="middle"
                  style="font-size:10px;font-weight:700;letter-spacing:1px;fill:#9ca3af">
                TOTAL CALLS
            </text>
            <text x="112" y="147" text-anchor="middle"
                  style="font-size:10px;font-weight:700;letter-spacing:1px;fill:#9ca3af">
                SINGLE/BULK
            </text>
        </svg>
        """,
        format_html("".join(map(str, paths))),
        breakdown["total"]
    )


