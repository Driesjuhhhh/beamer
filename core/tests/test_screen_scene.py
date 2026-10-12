import copy
import unittest

from core import ways


def mixed_layout():
    return {
        "A": dict(x=0, y=0, w=200, h=100,
                  displays={"a1": dict(x=0, y=0, w=100, h=100),
                            "a2": dict(x=100, y=0, w=100, h=100)},
                  display_offsets={"a2": dict(x=100, y=0)}),
        "B": dict(x=100, y=0, w=200, h=100,
                  displays={"b1": dict(x=0, y=0, w=100, h=100),
                            "b2": dict(x=100, y=0, w=100, h=100)},
                  display_offsets={"b2": dict(x=-100, y=100)})}


class ScreenSceneTests(unittest.TestCase):
    def test_resizing_keeps_other_screens_and_native_geometry_unchanged(self):
        layout = mixed_layout()
        before = copy.deepcopy(layout)
        resized = ways.resize_screen_layout(layout, 'B', 'b2', 145, 70)
        self.assertEqual(ways._display_frames(resized['B'])[1],
                         dict(display='b2', x=100, y=100, w=145, h=70))
        self.assertEqual(ways._display_frames(resized['B'])[0], ways._display_frames(layout['B'])[0])
        self.assertEqual(resized['B']['displays'], layout['B']['displays'])
        self.assertEqual(resized['A'], layout['A'])
        self.assertEqual(layout, before)
        self.assertTrue(ways._valid_tile_displays(resized['B']))
        self.assertEqual(ways.resize_screen_layout(layout, 'B', 'b2', -100, 9000)['B']['display_sizes']['b2'],
                         dict(w=40, h=4096))

    def test_nearby_edges_align_flush_without_a_distant_jump(self):
        target = dict(x=0, y=0, w=100, h=100)
        for screen, expected in (
            (dict(x=103, y=3, w=100, h=100), (100, 0)),
            (dict(x=100, y=-3, w=100, h=100), (100, 0)),
            (dict(x=3, y=103, w=100, h=100), (0, 100)),
            (dict(x=103, y=17, w=100, h=100), (100, 17)),
            (dict(x=106, y=3, w=100, h=100), (106, 3))):
            with self.subTest(screen=screen):
                snapped = ways.snap_screen_position(screen, [target], 4)
                self.assertEqual((snapped["x"], snapped["y"]), expected)

    def test_preview_snaps_only_the_selected_screen_and_is_stable(self):
        layout = mixed_layout()
        layout["B"]["display_offsets"]["b2"] = dict(x=-98, y=103)
        preview = ways.snap_screen_layout(layout, "B", "b2", 4)
        self.assertEqual(preview["B"]["display_offsets"]["b2"], dict(x=-100, y=100))
        self.assertEqual(preview["A"], layout["A"])
        self.assertEqual(preview, ways.snap_screen_layout(preview, "B", "b2", 4))
        self.assertEqual(preview, ways.snap_screen_layout(preview, "B", "b2", 0))

    def test_a_b_a_with_b_below_has_four_cards_and_only_real_screen_seams(self):
        layout = mixed_layout()
        before = copy.deepcopy(layout)
        cards, seams = ways.screen_scene(layout)
        self.assertEqual([(card["machine"], card["display"], card["frame"]["x"], card["frame"]["y"])
                          for card in cards],
                         [("A", "a1", 0, 0), ("A", "a2", 200, 0),
                          ("B", "b1", 100, 0), ("B", "b2", 100, 100)])
        self.assertEqual({(seam["start"], seam["end"]) for seam in seams},
                         {((100, 0), (100, 100)), ((200, 0), (200, 100))})
        self.assertEqual(layout, before)

    def test_third_pc_can_touch_the_lower_b_screen(self):
        layout = mixed_layout()
        layout["C"] = dict(x=100, y=200, w=100, h=100,
                           displays={"c1": dict(x=0, y=0, w=100, h=100)})
        cards, seams = ways.screen_scene(layout)
        self.assertEqual(len(cards), 5)
        self.assertIn(((100, 200), (200, 200)), [(s["start"], s["end"]) for s in seams])

    def test_unknown_machine_uses_one_placeholder_not_a_second_group_outline(self):
        layout = mixed_layout()
        layout["C"] = dict(x=500, y=0, w=100, h=100)
        cards, _seams = ways.screen_scene(layout)
        unknown = [card for card in cards if card["machine"] == "C"]
        self.assertEqual(len(unknown), 1)
        self.assertIsNone(unknown[0]["display"])
