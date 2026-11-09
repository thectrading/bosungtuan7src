import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image
import yaml

from turtlebot4_voice_nav.commands import RegionCatalog
from turtlebot4_voice_nav.segmentation import OccupancyMap, segment

ROOT = Path(__file__).resolve().parents[1]


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.catalog = RegionCatalog(ROOT/'maps/regions.json')

    def test_three_required_sentences(self):
        for phrase, route in [('Đi đến khu vực A.', ('A',)), ('Di chuyển từ khu vực A đến khu vực B.', ('A', 'B')),
                              ('Đi đến phòng thí nghiệm.', ('B',))]:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.catalog.parse(phrase).route, route)

    def test_extension_ordered_route(self):
        self.assertEqual(self.catalog.parse('Đi từ phòng A qua hành lang C rồi đến phòng B').route, ('A', 'C', 'B'))

    def test_unknown_anywhere_rejects_entire_route(self):
        for phrase in ['Đi đến khu vực Z', 'Đi từ A qua phòng Z rồi đến B', 'Đi từ A đến B đến Z']:
            result = self.catalog.parse(phrase)
            self.assertEqual(result.kind, 'UNKNOWN_REGION')
            self.assertEqual(result.route, ())

    def test_negation_unknown_acoustic_words_and_no_navigation_verb(self):
        for phrase in ['Không đi đến A', 'Đi đến [unk] A', 'phòng A', 'Xin chào']:
            self.assertNotEqual(self.catalog.parse(phrase).kind, 'NAVIGATE')

    def test_cancel_and_phonetic_aliases(self):
        for phrase in ['Dừng lại', 'Hủy điều hướng', 'stop']:
            self.assertEqual(self.catalog.parse(phrase).kind, 'CANCEL')
        self.assertEqual(self.catalog.parse('đi đến khu vực bê').route, ('B',))
        self.assertEqual(self.catalog.parse('đi đến khu vực xê').route, ('C',))

    def test_unknown_suffix_never_ignored(self):
        self.assertEqual(self.catalog.parse('Đi đến phòng học ngoài sân').kind, 'UNKNOWN_REGION')


class MapTests(unittest.TestCase):
    def test_cell_center_roundtrip_including_rotated_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new('L', (23, 17), 254).save(root/'grid.pgm')
            (root/'map.yaml').write_text(yaml.safe_dump(dict(image='grid.pgm', resolution=.07,
                                                            origin=[-3.7, 1.2, .63], negate=0, free_thresh=.196,
                                                            occupied_thresh=.65)))
            grid = OccupancyMap(root/'map.yaml')
            for col, row in [(0, 0), (22, 16), (8, 11)]:
                self.assertEqual(grid.world_to_pixel(*grid.pixel_to_world(col, row)), (col, row))

    def test_region_goals_are_free_clear_and_in_correct_region(self):
        grid = OccupancyMap(ROOT/'maps/map.yaml')
        data = json.loads((ROOT/'maps/regions.json').read_text())
        labels = np.load(ROOT/'maps/region_labels.npy')
        for i, region in enumerate(data['regions'], 1):
            goal = region['goal']
            self.assertTrue(grid.valid_goal(goal['x'], goal['y'], data['minimum_clearance_m']))
            col, row = grid.world_to_pixel(goal['x'], goal['y'])
            self.assertEqual(labels[row, col], i)
        self.assertTrue(np.all(labels[~grid.free] == 0))

    def test_disconnected_space_not_assigned_across_wall(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pixels = np.full((70, 100), 254, dtype=np.uint8)
            pixels[:, 49:52] = 0
            pixels[0, :] = pixels[-1, :] = 0
            pixels[:, 0] = pixels[:, -1] = 0
            Image.fromarray(pixels).save(root/'map.pgm')
            (root/'map.yaml').write_text(yaml.safe_dump(dict(image='map.pgm', resolution=.1,
                                                            origin=[0, 0, 0], negate=0, free_thresh=.196, occupied_thresh=.65)))
            seeds = [dict(id=str(i), name=str(i), aliases=[str(i)], seed=[1, y], goal=[1, y, 0]) for i, y in enumerate([1, 3, 5])]
            (root/'seeds.yaml').write_text(yaml.safe_dump(dict(regions=seeds, minimum_clearance_m=.2)))
            data = segment(root/'map.yaml', root/'seeds.yaml', root)
            labels = np.load(root/'region_labels.npy')
            self.assertTrue(np.all(labels[:, 52:] == 0))
            self.assertGreater(data['unassigned_free_cells'], 0)

    def test_unknown_pixels_and_unsafe_goals_are_rejected(self):
        grid = OccupancyMap(ROOT/'maps/map.yaml')
        self.assertFalse(grid.valid_goal(100, 100))
        self.assertFalse(grid.valid_goal(float('nan'), 0))
        pixels = np.argwhere(~grid.free)
        row, col = pixels[len(pixels)//2]
        self.assertFalse(grid.valid_goal(*grid.pixel_to_world(col, row)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
