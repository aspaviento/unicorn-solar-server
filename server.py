#!/usr/bin/env python3

import json
import os
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, make_response, request, send_from_directory
from flask_cors import CORS
from jsmin import jsmin

from lib.unicorn_wrapper import UnicornWrapper

FLOW_COLORS = {
    'charging': (0, 180, 80),
    'discharging': (230, 55, 60),
    'exporting': (30, 120, 255),
}
TARIFF_COLORS = {
    'low': (0, 180, 80),
    'medium': (255, 190, 0),
    'high': (230, 55, 60),
}
WHITE = (245, 248, 252)
BAR_START_COLUMNS = (14, 11, 8, 5, 2)
DISPLAY_WIDTH = 17
DISPLAY_HEIGHT = 7
DEFAULT_PORT = 9001

hardware_lock = threading.RLock()
unicorn = UnicornWrapper()
width, height = unicorn.getShape()
if (width, height) != (DISPLAY_WIDTH, DISPLAY_HEIGHT):
    raise RuntimeError(
        f'Unicorn Solar Server requires a 17x7 display, got {width}x{height}. '
        'Use a Unicorn HAT Mini at rotation 0.'
    )
state = {
    'percentage': 0,
    'flow': 'charging',
    'tariff': 'medium',
    'lastCalled': None,
    'lastCalledApi': None,
}


class SolarFlaskApp(Flask):
    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        if not self.debug or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
            with self.app_context():
                render_display()
        super().run(host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options)


app = SolarFlaskApp(__name__, static_folder='frontend/build', static_url_path='/')
CORS(app, resources={r'/api/*': {'origins': '*'}})


def read_json_body():
    raw = request.get_data(as_text=True) or '{}'
    try:
        content = json.loads(jsmin(raw))
    except ValueError:
        return None, make_response(jsonify({'error': 'Invalid JSON body'}), 400)
    if not isinstance(content, dict):
        return None, make_response(jsonify({'error': 'JSON body must be an object'}), 400)
    return content, None


def validate_choice(content, field, choices):
    value = content.get(field)
    if value not in choices:
        return None, f'{field} must be one of: {", ".join(choices)}'
    return value, None


def set_pixel(x, y, color):
    if 0 <= x < width and 0 <= y < height:
        unicorn.setPixel(x, y, *color)


def render_display():
    """Render the solar state as a horizontal battery on a 17x7 matrix."""
    active_bars = min(5, max(0, int((state['percentage'] + 19) // 20)))
    with hardware_lock:
        unicorn.clear()
        unicorn.setBrightness(0.5)
        for x in range(1, DISPLAY_WIDTH):
            set_pixel(x, 0, WHITE)
            set_pixel(x, 6, WHITE)
        for y in range(1, 6):
            set_pixel(1, y, WHITE)
            set_pixel(16, y, WHITE)
        for start_x in BAR_START_COLUMNS[:active_bars]:
            for x in (start_x, start_x + 1):
                for y in range(1, 6):
                    set_pixel(x, y, FLOW_COLORS[state['flow']])
        for y in (2, 3, 4):
            set_pixel(0, y, TARIFF_COLORS[state['tariff']])
        unicorn.show()


def touch(endpoint):
    state['lastCalledApi'] = endpoint
    state['lastCalled'] = datetime.now(timezone.utc).isoformat()


def status_payload():
    return {
        **state,
        'activeBars': min(5, max(0, int((state['percentage'] + 19) // 20))),
        'height': height,
        'rotation': unicorn.getRotation(),
        'width': width,
        'unicorn': unicorn.getType(),
    }


@app.route('/', methods=['GET'])
def root():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/battery', methods=['POST'])
def api_battery():
    content, error_response = read_json_body()
    if error_response is not None:
        return error_response
    percentage = content.get('percentage')
    if isinstance(percentage, bool) or not isinstance(percentage, (int, float)):
        return make_response(jsonify({'error': 'percentage must be a number'}), 400)
    if percentage < 0 or percentage > 100:
        return make_response(jsonify({'error': 'percentage must be between 0 and 100'}), 400)
    flow, error = validate_choice(content, 'flow', FLOW_COLORS)
    if error:
        return make_response(jsonify({'error': error}), 400)
    if flow == 'exporting' and percentage != 100:
        return make_response(jsonify({'error': 'exporting requires percentage to be 100'}), 400)
    state['percentage'] = percentage
    state['flow'] = flow
    touch('/api/battery')
    render_display()
    return jsonify(status_payload())


@app.route('/api/tariff', methods=['POST'])
def api_tariff():
    content, error_response = read_json_body()
    if error_response is not None:
        return error_response
    level, error = validate_choice(content, 'level', TARIFF_COLORS)
    if error:
        return make_response(jsonify({'error': error}), 400)
    state['tariff'] = level
    touch('/api/tariff')
    render_display()
    return jsonify(status_payload())


@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify(status_payload())


@app.errorhandler(404)
def not_found(_error):
    return make_response(jsonify({'error': 'Not found'}), 404)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('UNICORN_SOLAR_PORT', DEFAULT_PORT)), debug=False)
