import unittest
from unittest.mock import patch
from pathlib import Path

import server
from lib import unicorn_wrapper


class SolarServerTest(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        server.stop_animation()
        server.state.update({'percentage': 0, 'flow': 'charging', 'tariff': 'medium', 'displayMode': 'solar'})
        server.render_solar_display()

    def tearDown(self):
        server.stop_animation()

    def post_battery(self, percentage, flow='charging'):
        return self.client.post('/api/battery', json={'percentage': percentage, 'flow': flow})

    def test_battery_ranges_activate_expected_bars(self):
        expected = {
            0: 0,
            1: 1,
            20: 1,
            21: 2,
            40: 2,
            41: 3,
            60: 3,
            61: 4,
            80: 4,
            81: 5,
            100: 5,
        }
        for percentage, active_bars in expected.items():
            with self.subTest(percentage=percentage):
                response = self.post_battery(percentage)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['activeBars'], active_bars)

    def test_bars_fill_from_right_to_left(self):
        self.post_battery(20)
        self.assertEqual(server.unicorn.pixels[14][1], server.FLOW_COLORS['charging'])
        self.assertEqual(server.unicorn.pixels[11][1], (0, 0, 0))
        self.assertEqual(server.unicorn.pixels[2][1], (0, 0, 0))

        self.post_battery(40)
        self.assertEqual(server.unicorn.pixels[14][1], server.FLOW_COLORS['charging'])
        self.assertEqual(server.unicorn.pixels[11][1], server.FLOW_COLORS['charging'])
        self.assertEqual(server.unicorn.pixels[8][1], (0, 0, 0))

    def test_flow_sets_all_active_bars_to_its_color(self):
        for flow in ('charging', 'discharging'):
            with self.subTest(flow=flow):
                self.post_battery(100, flow)
                for start_x in server.BAR_START_COLUMNS:
                    self.assertEqual(server.unicorn.pixels[start_x][1], server.FLOW_COLORS[flow])

        self.post_battery(100, 'exporting')
        for start_x in server.BAR_START_COLUMNS:
            self.assertEqual(server.unicorn.pixels[start_x][1], server.FLOW_COLORS['exporting'])

    def test_exporting_requires_full_battery(self):
        response = self.post_battery(99, 'exporting')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error'], 'exporting requires percentage to be 100')

    def test_tariff_levels_set_all_terminal_pixels(self):
        for level in ('low', 'medium', 'high'):
            with self.subTest(level=level):
                response = self.client.post('/api/tariff', json={'level': level})
                self.assertEqual(response.status_code, 200)
                for y in (2, 3, 4):
                    self.assertEqual(server.unicorn.pixels[0][y], server.TARIFF_COLORS[level])

    def test_rejects_invalid_battery_values(self):
        self.assertEqual(self.post_battery(-1).status_code, 400)
        self.assertEqual(self.post_battery(101).status_code, 400)
        self.assertEqual(self.post_battery(50, 'idle').status_code, 400)

    def test_status_reports_complete_state(self):
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['width'], 17)
        self.assertEqual(response.json['height'], 7)
        self.assertEqual(response.json['rotation'], 0)
        self.assertEqual(response.json['displayMode'], 'solar')

    def test_api_index_lists_available_options(self):
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['endpoints']['off']['path'], '/api/off')
        self.assertEqual(response.json['endpoints']['rainbow']['path'], '/api/rainbow')

    def test_off_turns_off_every_pixel(self):
        self.post_battery(100, 'charging')
        response = self.client.post('/api/off')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['displayMode'], 'off')
        self.assertTrue(all(
            server.unicorn.pixels[x][y] == (0, 0, 0)
            for x in range(server.DISPLAY_WIDTH)
            for y in range(server.DISPLAY_HEIGHT)
        ))

    def test_rainbow_starts_and_solar_update_stops_animation(self):
        response = self.client.post('/api/rainbow', json={'brightness': 0.8, 'speed': 0.01})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['displayMode'], 'rainbow')
        self.assertIsNotNone(server.animation_thread)

        response = self.post_battery(20, 'charging')
        self.assertEqual(response.json['displayMode'], 'solar')
        self.assertIsNone(server.animation_thread)
        self.assertEqual(server.unicorn.pixels[14][1], server.FLOW_COLORS['charging'])

    def test_rainbow_rejects_invalid_values(self):
        self.assertEqual(self.client.post('/api/rainbow', json={'brightness': 2}).status_code, 400)
        self.assertEqual(self.client.post('/api/rainbow', json={'speed': 0}).status_code, 400)

    def test_display_contract_is_native_unicorn_hat_mini_shape(self):
        self.assertEqual((server.width, server.height), (17, 7))
        self.assertEqual((server.DISPLAY_WIDTH, server.DISPLAY_HEIGHT), (17, 7))

    def test_full_display_pattern_uses_expected_pixels(self):
        self.post_battery(100, 'exporting')
        self.client.post('/api/tariff', json={'level': 'high'})

        lit_pixels = [
            (x, y)
            for x in range(server.DISPLAY_WIDTH)
            for y in range(server.DISPLAY_HEIGHT)
            if server.unicorn.pixels[x][y] != (0, 0, 0)
        ]
        self.assertEqual(len(lit_pixels), 95)
        for x in range(1, 17):
            self.assertEqual(server.unicorn.pixels[x][0], server.WHITE)
            self.assertEqual(server.unicorn.pixels[x][6], server.WHITE)
        for y in range(1, 6):
            self.assertEqual(server.unicorn.pixels[1][y], server.WHITE)
            self.assertEqual(server.unicorn.pixels[16][y], server.WHITE)


class FakeMini:
    def __init__(self):
        self.rotation = None

    def set_brightness(self, _brightness):
        pass

    def set_rotation(self, rotation):
        self.rotation = rotation

    def get_shape(self):
        return (17, 7) if self.rotation == 0 else (7, 17)


class UnicornWrapperTest(unittest.TestCase):
    def test_mini_uses_native_17_by_7_rotation(self):
        with patch.object(unicorn_wrapper, 'UnicornHATMini', FakeMini):
            wrapper = unicorn_wrapper.UnicornWrapper('mini')
        self.assertEqual(wrapper.getRotation(), 0)
        self.assertEqual(wrapper.getShape(), (17, 7))


class InstallationIsolationTest(unittest.TestCase):
    def test_solar_service_is_distinct_from_busy_light_service(self):
        project_dir = Path(__file__).parent
        service = (project_dir / 'unicorn-solar.service').read_text()
        installers = (
            (project_dir / 'install.sh').read_text()
            + (project_dir / 'install-fallback.sh').read_text()
        )
        self.assertFalse((project_dir / 'busylight.service').exists())
        self.assertIn('Conflicts=busylight.service', service)
        self.assertIn('disable --now busylight.service', installers)
        self.assertNotIn('/etc/systemd/system/busylight.service', installers)
        self.assertIn('unicorn-solar.service', installers)
        self.assertIn('UNICORN_SOLAR_PORT=9001', service)
        self.assertIn('/home/pi/unicorn-solar-server/.venv/bin/python server.py', service)
        self.assertEqual(server.DEFAULT_PORT, 9001)

    def test_frontend_literals_are_centralized(self):
        project_dir = Path(__file__).parent
        app = (project_dir / 'frontend/src/components/app/App.tsx').read_text()
        self.assertNotIn('Bateria', app)
        self.assertNotIn('Porcentaje', app)
        self.assertNotIn('Tarifa', app)
        self.assertNotIn('Navegacion', app)
        self.assertIn("import { content } from '../../content';", app)


if __name__ == '__main__':
    unittest.main()
