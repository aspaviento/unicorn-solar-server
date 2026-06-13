#!/usr/bin/env python3

import json
import math
import os
import threading
from datetime import datetime, timezone
from time import monotonic, sleep

from flask import Flask, jsonify, make_response, request, send_from_directory
from flask_cors import CORS
from jsmin import jsmin

from lib.unicorn_wrapper import UnicornWrapper

BAR_COLORS = {
    'blue': (30, 120, 255),
    'green': (0, 180, 80),
    'red': (230, 55, 60),
    'yellow': (255, 190, 0),
}
FLOW_BAR_COLORS = {
    'charging': 'green',
    'discharging': 'red',
    'exporting': 'blue',
}
FLOW_COLORS = {
    flow: BAR_COLORS[color]
    for flow, color in FLOW_BAR_COLORS.items()
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
animation_thread = None
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
    'barColor': 'green',
    'tariff': 'medium',
    'displayMode': 'solar',
    'lastCalled': None,
    'lastCalledApi': None,
}


class SolarFlaskApp(Flask):
    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        if not self.debug or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
            with self.app_context():
                start_rainbow()
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


def validate_number(content, field, minimum, maximum, default):
    value = content.get(field, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, f'{field} must be a number'
    if value < minimum or value > maximum:
        return None, f'{field} must be between {minimum} and {maximum}'
    return value, None


def set_pixel(x, y, color):
    if 0 <= x < width and 0 <= y < height:
        unicorn.setPixel(x, y, *color)


def active_columns(percentage):
    return min(10, max(0, int(percentage // 10)))


def render_display():
    """Render the solar state as a horizontal battery on a 17x7 matrix."""
    columns_remaining = active_columns(state['percentage'])
    with hardware_lock:
        unicorn.clear()
        unicorn.setBrightness(0.5)
        for x in range(1, DISPLAY_WIDTH):
            set_pixel(x, 0, WHITE)
            set_pixel(x, 6, WHITE)
        for y in range(1, 6):
            set_pixel(1, y, WHITE)
            set_pixel(16, y, WHITE)
        for start_x in BAR_START_COLUMNS:
            for x in (start_x, start_x + 1):
                if columns_remaining <= 0:
                    break
                for y in range(1, 6):
                    set_pixel(x, y, BAR_COLORS[state['barColor']])
                columns_remaining -= 1
        for y in (2, 3, 4):
            set_pixel(0, y, TARIFF_COLORS[state['tariff']])
        unicorn.show()


def stop_animation():
    global animation_thread
    if animation_thread is not None:
        animation_thread.do_run = False
        if animation_thread != threading.current_thread():
            animation_thread.join(timeout=1)
        animation_thread = None


def sleep_while_running(thread, seconds):
    end = monotonic() + seconds
    while getattr(thread, 'do_run', True):
        remaining = end - monotonic()
        if remaining <= 0:
            return
        sleep(min(0.05, remaining))


def display_rainbow(brightness, speed):
    current_thread = threading.current_thread()
    offset = 30
    frame = 0.0
    while getattr(current_thread, 'do_run', True):
        frame += 0.3
        with hardware_lock:
            unicorn.setBrightness(brightness)
            for x in range(DISPLAY_WIDTH):
                for y in range(DISPLAY_HEIGHT):
                    red = (math.cos((x + frame) / 2.0) + math.cos((y + frame) / 2.0)) * 64.0 + 128.0
                    green = (math.sin((x + frame) / 1.5) + math.sin((y + frame) / 2.0)) * 64.0 + 128.0
                    blue = (math.sin((x + frame) / 2.0) + math.cos((y + frame) / 1.5)) * 64.0 + 128.0
                    set_pixel(
                        x,
                        y,
                        tuple(int(max(0, min(255, color + offset))) for color in (red, green, blue)),
                    )
            unicorn.show()
        sleep_while_running(current_thread, speed)


def start_rainbow(brightness=1, speed=0.1):
    global animation_thread
    stop_animation()
    state['displayMode'] = 'rainbow'
    animation_thread = threading.Thread(target=display_rainbow, args=(brightness, speed), daemon=True)
    animation_thread.do_run = True
    animation_thread.start()


def switch_off():
    stop_animation()
    state['displayMode'] = 'off'
    with hardware_lock:
        unicorn.clear()
        unicorn.off()


def render_solar_display():
    stop_animation()
    state['displayMode'] = 'solar'
    render_display()


def touch(endpoint):
    state['lastCalledApi'] = endpoint
    state['lastCalled'] = datetime.now(timezone.utc).isoformat()


def solaredge_error(message):
    return make_response(jsonify({'error': f'siteCurrentPowerFlow.{message}'}), 400)


def parse_solaredge_power_flow(content):
    power_flow = content.get('siteCurrentPowerFlow')
    if not isinstance(power_flow, dict):
        return None, solaredge_error('must be an object')

    storage = power_flow.get('STORAGE')
    if not isinstance(storage, dict):
        return None, solaredge_error('STORAGE must be an object')
    percentage = storage.get('chargeLevel')
    if isinstance(percentage, bool) or not isinstance(percentage, (int, float)):
        return None, solaredge_error('STORAGE.chargeLevel must be a number')
    if percentage < 0 or percentage > 100:
        return None, solaredge_error('STORAGE.chargeLevel must be between 0 and 100')

    grid = power_flow.get('GRID')
    if not isinstance(grid, dict):
        return None, solaredge_error('GRID must be an object')
    grid_power = grid.get('currentPower')
    if isinstance(grid_power, bool) or not isinstance(grid_power, (int, float)):
        return None, solaredge_error('GRID.currentPower must be a number')

    connections = power_flow.get('connections')
    if not isinstance(connections, list):
        return None, solaredge_error('connections must be an array')
    sources = []
    for connection in connections[:2]:
        if not isinstance(connection, dict) or not isinstance(connection.get('from'), str):
            return None, solaredge_error('connections must contain objects with a from value')
        sources.append(connection['from'].upper())

    imports_energy = any(source in ('GRID', 'STORAGE') for source in sources)
    if imports_energy:
        bar_color = 'red'
    elif grid_power > 2:
        bar_color = 'blue'
    elif grid_power > 1:
        bar_color = 'green'
    else:
        bar_color = 'yellow'

    storage_status = storage.get('status')
    if not isinstance(storage_status, str):
        return None, solaredge_error('STORAGE.status must be a string')
    normalized_status = storage_status.lower()
    if normalized_status == 'charging':
        flow = 'charging'
    elif normalized_status == 'discharging' or bar_color == 'red':
        flow = 'discharging'
    else:
        flow = 'exporting'

    return {
        'barColor': bar_color,
        'flow': flow,
        'percentage': percentage,
    }, None


def status_payload():
    columns = active_columns(state['percentage'])
    return {
        **state,
        'activeBlocks': columns // 2,
        'activeColumns': columns,
        'height': height,
        'rotation': unicorn.getRotation(),
        'width': width,
        'unicorn': unicorn.getType(),
    }


@app.route('/', methods=['GET'])
def root():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/', methods=['GET'])
def api_index():
    return jsonify({
        'endpoints': {
            'battery': {'methods': ['POST'], 'path': '/api/battery'},
            'off': {'methods': ['GET', 'POST'], 'path': '/api/off'},
            'rainbow': {'methods': ['POST'], 'path': '/api/rainbow'},
            'solaredgeInterface': {'methods': ['POST'], 'path': '/api/solaredge-interface'},
            'status': {'methods': ['GET'], 'path': '/api/status'},
            'tariff': {'methods': ['POST'], 'path': '/api/tariff'},
        }
    })


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
    state['barColor'] = FLOW_BAR_COLORS[flow]
    touch('/api/battery')
    render_solar_display()
    return jsonify(status_payload())


@app.route('/api/solaredge-interface', methods=['POST'])
def api_solaredge_interface():
    content, error_response = read_json_body()
    if error_response is not None:
        return error_response
    solar_state, error_response = parse_solaredge_power_flow(content)
    if error_response is not None:
        return error_response
    state.update(solar_state)
    touch('/api/solaredge-interface')
    render_solar_display()
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
    render_solar_display()
    return jsonify(status_payload())


@app.route('/api/off', methods=['GET', 'POST'])
def api_off():
    touch('/api/off')
    switch_off()
    return jsonify(status_payload())


@app.route('/api/rainbow', methods=['POST'])
def api_rainbow():
    content, error_response = read_json_body()
    if error_response is not None:
        return error_response
    brightness, error = validate_number(content, 'brightness', 0, 1, 1)
    if error:
        return make_response(jsonify({'error': error}), 400)
    speed, error = validate_number(content, 'speed', 0.01, 60, 0.1)
    if error:
        return make_response(jsonify({'error': error}), 400)
    touch('/api/rainbow')
    start_rainbow(brightness, speed)
    return jsonify(status_payload())


@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify(status_payload())


@app.errorhandler(404)
def not_found(_error):
    return make_response(jsonify({'error': 'Not found'}), 404)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('UNICORN_SOLAR_PORT', DEFAULT_PORT)), debug=False)
