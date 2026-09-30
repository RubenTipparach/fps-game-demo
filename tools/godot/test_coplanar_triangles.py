"""The triangle-level z-fighting check (CLAUDE.md 7.2; openspec/changes/archive/2026-09-30-cc0-vehicles, design
section 6): detailing.coplanar_triangle_report finds faces of one mesh that share a plane, face the
same way and overlap, which is how a converted pack model, built from no registered boxes, is
held to the rule.

    python3 -m unittest discover -s tools/godot -p 'test_*.py'
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detailing as D  # noqa: E402

QUAD = [((0, 0, 0), (1, 0, 0), (1, 1, 0)), ((0, 0, 0), (1, 1, 0), (0, 1, 0))]


def decal(z, flip=False):
    """A small triangle over the quad's middle at height z, facing up (or down)."""
    a, b, c = (0.2, 0.2, z), (0.6, 0.2, z), (0.6, 0.6, z)
    return (a, c, b) if flip else (a, b, c)


class CoplanarTriangles(unittest.TestCase):
    def test_the_two_halves_of_a_quad_touch_but_do_not_overlap(self):
        self.assertEqual([], D.coplanar_triangle_report(QUAD), "neighbours sharing an edge draw no pixel twice")

    def test_a_decal_laid_flush_on_a_face_is_found(self):
        self.assertEqual([(0, 2)], D.coplanar_triangle_report(QUAD + [decal(0.001)]),
                         "1 mm off the face is inside the 5 mm the checker treats as coplanar")

    def test_faces_back_to_back_are_fine(self):
        self.assertEqual([], D.coplanar_triangle_report(QUAD + [decal(0.0, flip=True)]),
                         "a face turned the other way is never drawn from the same side")

    def test_a_face_standing_a_centimetre_proud_is_fine(self):
        self.assertEqual([], D.coplanar_triangle_report(QUAD + [decal(0.01)]),
                         "CLAUDE.md 7.2: deliberately parallel surfaces keep at least 1 cm apart")

    def test_a_degenerate_triangle_is_skipped(self):
        self.assertEqual([], D.coplanar_triangle_report(QUAD + [((0, 0, 0), (1, 0, 0), (2, 0, 0))]))


if __name__ == "__main__":
    unittest.main()
