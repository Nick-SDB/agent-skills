"""Validate portable instruction-flow SVG structure and arrow geometry."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


SVG = "{http://www.w3.org/2000/svg}"
NUMBER = re.compile(r"^-?(?:\d+(?:\.\d*)?|\.\d+)$")
FONT_SIZE = re.compile(r"font-size\s*:\s*(\d+(?:\.\d+)?)px\b")
MARKER_REFERENCE = re.compile(r"^url\(#([A-Za-z_][\w:.-]*)\)$")
FORBIDDEN_ELEMENTS = {"script", "image", "foreignObject"}


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def number(value: str, context: str) -> float:
    if not NUMBER.fullmatch(value.strip()):
        raise ValueError(f"{context} must be a plain numeric SVG value")
    return float(value)


def points(value: str, context: str) -> list[tuple[float, float]]:
    parsed: list[tuple[float, float]] = []
    for token in value.split():
        pair = token.split(",")
        if len(pair) != 2:
            raise ValueError(f"{context} contains an invalid point: {token}")
        parsed.append((number(pair[0], context), number(pair[1], context)))
    if len(parsed) < 2:
        raise ValueError(f"{context} must contain at least two points")
    return parsed


def segment_crosses_box(
    start: tuple[float, float], end: tuple[float, float], box: Box
) -> bool:
    x1, y1 = start
    x2, y2 = end
    if y1 == y2 and box.y < y1 < box.y + box.height:
        low, high = sorted((x1, x2))
        return max(low, box.x) < min(high, box.x + box.width)
    if x1 == x2 and box.x < x1 < box.x + box.width:
        low, high = sorted((y1, y2))
        return max(low, box.y) < min(high, box.y + box.height)
    return False


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        return [f"cannot parse SVG: {error}"]

    if root.tag != SVG + "svg":
        return ["root element must be an SVG"]

    view_box_text = root.attrib.get("viewBox", "")
    try:
        view_box = [number(value, "viewBox") for value in view_box_text.split()]
        if len(view_box) != 4 or view_box[2] <= 0 or view_box[3] <= 0:
            raise ValueError
    except ValueError:
        return ["viewBox must contain four numeric values with positive width and height"]
    min_x, min_y, width, height = view_box
    max_x, max_y = min_x + width, min_y + height

    for required in ("title", "desc"):
        element = root.find(SVG + required)
        if element is None or not "".join(element.itertext()).strip():
            errors.append(f"missing nonempty <{required}>")

    font_sizes: list[float] = []
    label_boxes: list[Box] = []
    markers: dict[str, ET.Element] = {}
    arrows: list[tuple[ET.Element, list[tuple[float, float]]]] = []

    for element in root.iter():
        name = local_name(element.tag)
        if name in FORBIDDEN_ELEMENTS:
            errors.append(f"external resources are not allowed: <{name}>")
        for attribute, value in element.attrib.items():
            if local_name(attribute) == "href" and not value.startswith("#"):
                errors.append("external resources are not allowed: href")

        if name == "style" and element.text:
            font_sizes.extend(float(match) for match in FONT_SIZE.findall(element.text))
        if "font-size" in element.attrib:
            try:
                font_size = element.attrib["font-size"]
                if font_size.endswith("px"):
                    font_size = font_size[:-2]
                font_sizes.append(number(font_size, "font-size"))
            except ValueError as error:
                errors.append(str(error))

        if "data-label-box" in element.attrib:
            try:
                values = [number(value, "data-label-box") for value in element.attrib["data-label-box"].split()]
                if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
                    raise ValueError
                box = Box(*values)
                label_boxes.append(box)
                if not (
                    min_x <= box.x
                    and min_y <= box.y
                    and box.x + box.width <= max_x
                    and box.y + box.height <= max_y
                ):
                    errors.append("data-label-box extends outside viewBox")
            except ValueError:
                errors.append("data-label-box must contain x y width height")

        if name == "marker" and "id" in element.attrib:
            markers[element.attrib["id"]] = element

        marker_end = element.attrib.get("marker-end")
        if marker_end:
            if name == "line":
                try:
                    arrow_points = [
                        (number(element.attrib["x1"], "line"), number(element.attrib["y1"], "line")),
                        (number(element.attrib["x2"], "line"), number(element.attrib["y2"], "line")),
                    ]
                except (KeyError, ValueError) as error:
                    errors.append(f"invalid arrow line: {error}")
                    continue
            elif name == "polyline":
                try:
                    arrow_points = points(element.attrib.get("points", ""), "polyline")
                except ValueError as error:
                    errors.append(str(error))
                    continue
            else:
                errors.append("arrow shafts must use <line> or <polyline>")
                continue
            arrows.append((element, arrow_points))

    if arrows and not label_boxes:
        errors.append("arrow diagrams must declare data-label-box clearance regions")

    minimum_font = min(font_sizes) if font_sizes else None
    if arrows and minimum_font is None:
        errors.append("cannot size arrowheads without a numeric font-size")

    for element, arrow_points in arrows:
        for start, end in zip(arrow_points, arrow_points[1:]):
            if start[0] != end[0] and start[1] != end[1]:
                errors.append("arrow segments must be horizontal or vertical")
            for box in label_boxes:
                if segment_crosses_box(start, end, box):
                    errors.append("arrow crosses data-label-box")

        marker_match = MARKER_REFERENCE.fullmatch(element.attrib["marker-end"])
        if not marker_match or marker_match.group(1) not in markers:
            errors.append("arrow marker-end must reference a local marker")
            continue
        marker = markers[marker_match.group(1)]
        if marker.attrib.get("markerUnits") != "userSpaceOnUse":
            errors.append("arrow markers must use markerUnits=userSpaceOnUse")
        try:
            marker_width = number(marker.attrib.get("markerWidth", ""), "markerWidth")
        except ValueError as error:
            errors.append(str(error))
            continue
        arrowhead_width = marker_width
        for polygon in marker.findall(".//" + SVG + "polygon"):
            try:
                polygon_points = points(polygon.attrib.get("points", ""), "marker polygon")
                polygon_x = [x for x, _ in polygon_points]
                arrowhead_width = max(arrowhead_width, max(polygon_x) - min(polygon_x))
            except ValueError as error:
                errors.append(str(error))
        if minimum_font is not None and arrowhead_width > minimum_font:
            errors.append(
                f"arrowhead width {arrowhead_width:g} exceeds minimum font size {minimum_font:g}"
            )

    def in_bounds(x: float, y: float) -> bool:
        return min_x <= x <= max_x and min_y <= y <= max_y

    for element in root.iter():
        name = local_name(element.tag)
        try:
            if name == "rect":
                x = number(element.attrib.get("x", "0"), "rect x")
                y = number(element.attrib.get("y", "0"), "rect y")
                rect_width = number(element.attrib["width"], "rect width")
                rect_height = number(element.attrib["height"], "rect height")
                if not (in_bounds(x, y) and in_bounds(x + rect_width, y + rect_height)):
                    errors.append("rect extends outside viewBox")
            elif name == "circle":
                x = number(element.attrib["cx"], "circle cx")
                y = number(element.attrib["cy"], "circle cy")
                radius = number(element.attrib["r"], "circle r")
                if not (in_bounds(x - radius, y - radius) and in_bounds(x + radius, y + radius)):
                    errors.append("circle extends outside viewBox")
            elif name == "line":
                for x_key, y_key in (("x1", "y1"), ("x2", "y2")):
                    if not in_bounds(number(element.attrib[x_key], "line"), number(element.attrib[y_key], "line")):
                        errors.append("line extends outside viewBox")
            elif name == "polyline":
                if not all(in_bounds(x, y) for x, y in points(element.attrib.get("points", ""), "polyline")):
                    errors.append("polyline extends outside viewBox")
        except (KeyError, ValueError) as error:
            errors.append(f"invalid {name} geometry: {error}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", nargs="+", type=Path, help="SVG file to validate")
    arguments = parser.parse_args()

    failed = False
    for path in arguments.svg:
        for error in validate(path):
            failed = True
            print(f"{path}: {error}", file=sys.stderr)
    if failed:
        return 1

    noun = "SVG" if len(arguments.svg) == 1 else "SVGs"
    print(f"validated {len(arguments.svg)} {noun}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
