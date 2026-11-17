import datetime as dt
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import heartbeat


class HeartbeatTests(unittest.TestCase):
    def test_field_columns_are_bounded(self):
        rows = heartbeat.field(110)
        self.assertEqual(len(rows), 11)
        self.assertTrue(all(len(x) == 30 for x in rows))

    def test_phase_bounds(self):
        x = heartbeat.phase_fraction(dt.datetime(2026, 11, 18, tzinfo=dt.timezone.utc))
        self.assertGreaterEqual(x, 0)
        self.assertLess(x, 1)

    def test_hides_private_details_and_repo_names(self):
        sample = [{
            'actor': {'login': 'robdroid0110'},
            'repo': {'name': 'robdroid0110/REDACTED_REPO'},
            'type': 'PushEvent',
            'created_at': '2026-11-18T10:01:00Z',
            'payload': {'commits': [{'message': 'SECRET_MESSAGE'}]},
        }]
        with patch.object(heartbeat, 'fetch_events', return_value=sample):
            with patch.object(heartbeat, 'ROOT', pathlib.Path('/tmp')):
                # rendering itself never includes repository or commit metadata.
                state = {'sampled_at':'2026-11-18T10:00:00Z', 'feed_status':'sampled',
                         'sample_size':1, 'push_count':1, 'lunar_phase':0.3, 'seed':110}
                result = heartbeat.render(state)
                self.assertNotIn('REDACTED_REPO', result)
                self.assertNotIn('SECRET_MESSAGE', result)

    def test_markers_unique(self):
        readme = heartbeat.README.read_text(encoding='utf-8')
        self.assertEqual(readme.count(heartbeat.BEGIN), 1)
        self.assertEqual(readme.count(heartbeat.END), 1)
        self.assertNotIn('![', readme)
        self.assertNotIn('.svg', readme)

if __name__ == '__main__':
    unittest.main()
