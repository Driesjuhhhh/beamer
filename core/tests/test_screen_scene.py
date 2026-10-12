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
