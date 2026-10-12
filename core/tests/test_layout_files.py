import copy
from pathlib import Path
import tempfile
import unittest

from core import crossing_state, layout_files
from core.tests.test_crossing_state import OWN, A, B, settings, tile


class LayoutFilesTests(unittest.TestCase):
    def test_roundtrip_restores_positions_and_sizes_without_connection_secrets(self):
        held = settings()
        held['layout'][OWN] = tile(displays={'0': dict(x=0, y=0, w=1920, h=1080)})
        held['layout'][OWN]['display_sizes'] = {'0': dict(w=160, h=100)}
        held['layout'][OWN]['display_offsets'] = {'0': dict(x=0, y=0)}
        held['peers'][0]['token'] = 'secret-token'
        root = Path(__file__).resolve().parents[2] / 'renders' / 'test-tmp'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            path = Path(directory) / 'work.json'
            layout_files.write(path, held)
            self.assertNotIn('secret-token', path.read_text())
            tiles = layout_files.read(path)
        changed = copy.deepcopy(held)
        changed['layout'][OWN]['display_sizes']['0']['w'] = 80
        changed['layout'][A]['x'] = 300
        # Native monitor geometry can change after saving; never restore it.
        changed['layout'][OWN]['displays']['0']['w'] = 2560
        changed['layout'][B] = tile(900)
        changed['peers'].append({'id': B, 'port': 24820, 'side': 'right'})
        out = crossing_state.restore_layout(changed, tiles, platform='pc', capable={OWN, A, B},
                                            live=lambda _: True, gone=lambda _: False, now=100)
        self.assertEqual(out['settings']['layout'][A]['x'], 160)
        self.assertEqual(out['settings']['layout'][OWN]['display_sizes']['0']['w'], 160)
        self.assertEqual(out['settings']['layout'][OWN]['displays']['0']['w'], 2560)
        self.assertEqual(out['settings']['layout'][B], changed['layout'][B])
        self.assertEqual(out['settings']['peers'][0]['token'], 'secret-token')
        self.assertTrue(out['send_picture'])
        self.assertGreater(out['settings']['layout_set_at'], changed['layout_set_at'])

    def test_invalid_file_rejected(self):
        with self.assertRaises(ValueError):
            layout_files.validate({'format': 'beamer-crossing-layout', 'version': 1,
                                   'machine_id': OWN, 'tiles': {OWN: tile(w=-2)}})

    def test_foreign_layout_rejected_without_mutating_settings(self):
        held = settings()
        before = copy.deepcopy(held)
        with self.assertRaises(ValueError):
            crossing_state.restore_layout(held, {A: tile()}, platform='pc', capable={OWN, A},
                                          live=lambda _: True, gone=lambda _: False, now=100)
        self.assertEqual(held, before)
