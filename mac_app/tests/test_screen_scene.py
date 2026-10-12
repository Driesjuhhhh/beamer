import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import AppKit
import diagram
from core.tests.test_screen_scene import mixed_layout


class ScreenCanvasTests(unittest.TestCase):
    def test_mixed_machines_render_only_four_independent_screen_cards(self):
        AppKit.NSApplication.sharedApplication()
        canvas = diagram.AtlasCanvas.alloc().init().setup()
        canvas.setFrame_(((0, 0), (720, 300)))
        layout = mixed_layout()
        canvas.show_layout(layout, {"B": {"platform": "Windows", "linked": True}},
                           {"A": "PC A", "B": "PC B"}, "A", "B")
        canvas._draw(False)
        self.assertTrue(all(layer.isHidden() for layer in canvas.layer_for_tile.values()))
        self.assertTrue(all(layer.isHidden() for layer in canvas.label_for_tile.values()))
        self.assertTrue(all(layer.isHidden() for layer in canvas.grid_layers))
        self.assertEqual(len(canvas.display_layers["A"]), 2)
        self.assertEqual(len(canvas.display_layers["B"]), 2)
        self.assertEqual(canvas.display_layers["A"][0].sublayers()[0].string(), "PC A · Screen 1")
        self.assertEqual(canvas.display_layers["B"][1].sublayers()[0].string(), "PC B · Screen 2")
        self.assertEqual(len(canvas.contact_layers), 2)
        self.assertEqual(canvas._third_segments(canvas._map()[0]), [])
        a1, a2 = [layer.frame() for layer in canvas.display_layers["A"]]
        b1, b2 = [layer.frame() for layer in canvas.display_layers["B"]]
        self.assertAlmostEqual(a1.origin.x+a1.size.width, b1.origin.x)
        self.assertAlmostEqual(b1.origin.x+b1.size.width, a2.origin.x)
        self.assertAlmostEqual(b1.origin.y+b1.size.height, b2.origin.y)
        canvas.identify({'A': 'A'})
        self.assertEqual(canvas.display_layers['A'][0].sublayers()[1].string(), 'A1')
        self.assertEqual(canvas.display_layers['A'][1].sublayers()[1].string(), 'A2')
        self.assertNotEqual(canvas.display_layers['B'][0].sublayers()[1].string(), 'B1')
