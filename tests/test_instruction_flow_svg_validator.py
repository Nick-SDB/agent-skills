from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    ROOT
    / "skills"
    / "general"
    / "create-instruction-flow-svg"
    / "scripts"
    / "validate_instruction_flow_svg.py"
)


VALID_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 140">
  <title>Pipeline</title>
  <desc>Instruction-level pipeline with orthogonal data flow.</desc>
  <defs>
    <marker id="arrow" markerUnits="userSpaceOnUse" markerWidth="8" markerHeight="8"
            refX="7" refY="4" orient="auto">
      <polygon points="0,0 8,4 0,8"/>
    </marker>
    <style>.small { font-size: 12px; }</style>
  </defs>
  <rect width="240" height="140" fill="#fff"/>
  <g data-label-box="20 18 70 22">
    <rect x="20" y="18" width="70" height="22"/>
    <text class="small" x="55" y="33" text-anchor="middle">load</text>
  </g>
  <polyline points="20,70 120,70 120,110 210,110"
            fill="none" marker-end="url(#arrow)"/>
</svg>
"""


def run_validator(svg: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as temp_text:
        path = Path(temp_text) / "diagram.svg"
        path.write_text(textwrap.dedent(svg).strip() + "\n", encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(path)],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=10,
        )


class InstructionFlowSvgValidatorTests(unittest.TestCase):
    def test_accepts_orthogonal_flow_with_label_clearance(self) -> None:
        result = run_validator(VALID_SVG)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("validated 1 SVG", result.stdout)

    def test_rejects_diagonal_arrow_segment(self) -> None:
        svg = VALID_SVG.replace(
            'points="20,70 120,70 120,110 210,110"',
            'points="20,70 120,80 120,110 210,110"',
        )
        result = run_validator(svg)
        self.assertEqual(result.returncode, 1)
        self.assertIn("arrow segments must be horizontal or vertical", result.stderr)

    def test_rejects_arrow_crossing_declared_label_box(self) -> None:
        svg = VALID_SVG.replace('data-label-box="20 18 70 22"', 'data-label-box="70 60 35 20"')
        result = run_validator(svg)
        self.assertEqual(result.returncode, 1)
        self.assertIn("arrow crosses data-label-box", result.stderr)

    def test_rejects_arrowhead_wider_than_smallest_font(self) -> None:
        svg = VALID_SVG.replace('markerWidth="8"', 'markerWidth="13"')
        result = run_validator(svg)
        self.assertEqual(result.returncode, 1)
        self.assertIn("arrowhead width 13 exceeds minimum font size 12", result.stderr)

    def test_rejects_triangle_wider_than_smallest_font(self) -> None:
        svg = VALID_SVG.replace('points="0,0 8,4 0,8"', 'points="0,0 13,4 0,8"')
        result = run_validator(svg)
        self.assertEqual(result.returncode, 1)
        self.assertIn("arrowhead width 13 exceeds minimum font size 12", result.stderr)

    def test_rejects_external_resources(self) -> None:
        svg = VALID_SVG.replace(
            "</svg>", '<image href="https://example.com/pixel.png"/></svg>'
        )
        result = run_validator(svg)
        self.assertEqual(result.returncode, 1)
        self.assertIn("external resources are not allowed", result.stderr)


if __name__ == "__main__":
    unittest.main()
