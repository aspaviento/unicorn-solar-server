import os
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

os.environ['UNICORN_FORCE_DUMMY'] = '1'
import server
from lib import consumption_schedule as schedule


class ConsumptionScheduleTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'settings.json'
        self.environment = patch.dict(os.environ, {'UNICORN_SOLAR_SETTINGS_PATH': str(self.path)})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.settings = patch.object(server, 'consumption_settings', dict(schedule.DEFAULT_SETTINGS))
        self.settings.start()
        self.addCleanup(self.settings.stop)
        self.old_state = dict(server.state)
        self.addCleanup(server.state.update, self.old_state)
        self.active = patch.object(server, 'consumption_active', False)
        self.active.start()
        self.addCleanup(self.active.stop)
        server.stop_animation()
        server.state['displayMode'] = 'solar'
        self.client = server.app.test_client()

    def test_daily_boundaries_and_overnight(self):
        settings = schedule.validate_settings({'windows': '08:00-09:00,23:30-00:30', 'timezone': 'UTC'})
        for hour, minute, expected in [(7,59,False),(8,0,True),(8,59,True),(9,0,False),
                                       (23,30,True),(0,29,True),(0,30,False)]:
            with self.subTest(hour=hour, minute=minute):
                self.assertEqual(schedule.is_active(settings, datetime(2026,1,1,hour,minute,tzinfo=timezone.utc)), expected)

    def test_timezone_and_both_dst_changes(self):
        settings = {'windows': '02:00-03:00', 'timezone': 'Europe/Madrid'}
        for date, expected in [('2026-10-25T00:30:00+00:00',True),
                               ('2026-10-25T01:30:00+00:00',True),
                               ('2026-10-25T02:00:00+00:00',False),
                               ('2026-03-29T00:59:00+00:00',False),
                               ('2026-03-29T01:00:00+00:00',False)]:
            self.assertEqual(schedule.is_active(settings, datetime.fromisoformat(date)), expected)
        settings['windows'] = '08:00-09:00'
        self.assertTrue(schedule.is_active(settings, datetime.fromisoformat('2026-01-01T07:00:00+00:00')))
        self.assertTrue(schedule.is_active(settings, datetime.fromisoformat('2026-07-01T06:00:00+00:00')))

    def test_save_read_reload_and_empty_disable(self):
        self.assertEqual(schedule.load_settings(), schedule.DEFAULT_SETTINGS)
        data = {'windows': ' 08:00-09:00, 12:00-14:00 ', 'timezone': 'UTC'}
        response = self.client.post('/api/settings', json=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['windows'], '08:00-09:00,12:00-14:00')
        self.assertEqual(schedule.load_settings(), response.json)
        self.assertEqual(self.client.get('/api/settings').json, response.json)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.client.post('/api/settings', json={'windows': '', 'timezone': 'UTC'})
        self.assertFalse(self.client.get('/api/status').json['highConsumptionExpected'])

    def test_invalid_settings_preserve_last_valid_configuration(self):
        valid = {'windows': '08:00-09:00', 'timezone': 'UTC'}
        self.client.post('/api/settings', json=valid)
        before = self.path.read_bytes()
        for windows in ['25:00-26:00','08:60-09:00','8:00-09:00','08:00-08:00','08:00-09:00,',None,[],True]:
            with self.subTest(windows=windows):
                self.assertEqual(self.client.post('/api/settings', json={'windows': windows,'timezone':'UTC'}).status_code,400)
        self.assertEqual(self.client.post('/api/settings',json={'windows':'','timezone':'Invalid/Zone'}).status_code,400)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(server.consumption_settings,valid)

    def test_write_failure_keeps_runtime_and_file(self):
        valid = {'windows': '08:00-09:00', 'timezone': 'UTC'}
        self.client.post('/api/settings', json=valid)
        with patch.object(schedule.os, 'replace', side_effect=OSError('write failure')):
            with self.assertLogs(server.app.logger, level='ERROR'):
                response = self.client.post('/api/settings',json={'windows':'','timezone':'UTC'})
        self.assertEqual(response.status_code,500)
        self.assertEqual(server.consumption_settings, valid)
        self.assertEqual(schedule.load_settings(), valid)
        self.assertEqual(list(self.path.parent.iterdir()),[self.path])

    def test_transition_only_changes_outline_without_new_solar_data(self):
        server.state.update(percentage=70,tariff='low',barColor='yellow')
        server.render_display()
        before = deepcopy(server.unicorn.pixels)
        previous_update = server.state['lastCalled']
        with patch.object(schedule,'is_active',return_value=True):
            server.refresh_consumption_schedule()
            self.assertTrue(self.client.get('/api/status').json['highConsumptionExpected'])
        for x in range(17):
            for y in range(7):
                outline = (x>=1 and y in (0,6)) or (x in (1,16) and 1<=y<=5)
                self.assertEqual(server.unicorn.pixels[x][y],schedule.VIOLET if outline else before[x][y])
        with patch.object(schedule,'is_active',return_value=False):
            server.refresh_consumption_schedule()
        self.assertEqual(server.unicorn.pixels,before)
        self.assertEqual(server.state['lastCalled'],previous_update)

    def test_schedule_never_wakes_other_modes(self):
        for mode in ['off','standby','rainbow']:
            server.state['displayMode'] = mode
            server.consumption_active = False
            with patch.object(schedule,'is_active',return_value=True), patch.object(server,'render_display') as draw:
                server.refresh_consumption_schedule()
                draw.assert_not_called()
            self.assertEqual(server.state['displayMode'],mode)


if __name__ == '__main__':
    unittest.main()
