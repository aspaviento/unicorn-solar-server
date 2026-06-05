#!/usr/bin/env python

import json

import os
import threading
import math
from time import sleep
from time import monotonic
from datetime import datetime
from gpiozero import CPUTemperature
from lib.unicorn_wrapper import UnicornWrapper
from flask import Flask, jsonify, make_response, request, send_from_directory
from flask_cors import CORS
from random import randint
from jsmin import jsmin

blinkThread = None
hardwareLock = threading.RLock()
crntColors = None
globalRed = 0
globalGreen = 0
globalBlue = 0
globalBrightness = 0
globalLastCalled = None
globalLastCalledApi = None
globalStatus = None
globalStatusOverwrite = False

# Initialize the Unicorn hat
unicorn = UnicornWrapper()

# get the width and height of the hardware and set it to portrait if its not
width, height = unicorn.getShape()


class MyFlaskApp(Flask):
	def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
		if not self.debug or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
			with self.app_context():
				startupRainbow()
		super(MyFlaskApp, self).run(host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options)


app = MyFlaskApp(__name__, static_folder='frontend/build', static_url_path='/')
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})


def setColor(r, g, b, brightness=0.5, speed=None):
	global crntColors
	setPixels(r, g, b, brightness)
	with hardwareLock:
		unicorn.show()

	if speed is not None and speed != '':
		crntT = threading.current_thread()
		with hardwareLock:
			unicorn.clear()
		while getattr(crntT, "do_run", True):
			setPixels(r, g, b, brightness)
			with hardwareLock:
				unicorn.show()
			sleepWhileRunning(crntT, speed)
			with hardwareLock:
				unicorn.clear()
				unicorn.show()
			sleepWhileRunning(crntT, speed)


def sleepWhileRunning(thread, seconds):
	end = monotonic() + seconds
	while getattr(thread, "do_run", True):
		remaining = end - monotonic()
		if remaining <= 0:
			return
		sleep(min(0.1, remaining))


def setPixels(r, g, b, brightness=0.5):
	global globalBrightness, globalBlue, globalGreen, globalRed

	globalRed = r
	globalGreen = g
	globalBlue = b

	if brightness is not None:
		globalBrightness = brightness
		with hardwareLock:
			unicorn.setBrightness(brightness)

	with hardwareLock:
		unicorn.setColour(r, g, b)


def startAnimation(target, args):
	global blinkThread
	switchOff()
	blinkThread = threading.Thread(target=target, args=args, daemon=True)
	blinkThread.do_run = True
	blinkThread.start()


def readJsonBody():
	raw = request.get_data(as_text=True) or '{}'
	try:
		content = json.loads(jsmin(raw))
	except ValueError:
		return None, make_response(jsonify({'error': 'Invalid JSON body'}), 400)

	if not isinstance(content, dict):
		return None, make_response(jsonify({'error': 'JSON body must be an object'}), 400)

	return content, None


def getNumber(content, field, minimum, maximum, required=False):
	value = content.get(field, None)
	if value is None:
		if required:
			return None, f'{field} must be present'
		return None, None

	if isinstance(value, bool) or not isinstance(value, (int, float)):
		return None, f'{field} must be a number'

	if value < minimum or value > maximum:
		return None, f'{field} must be between {minimum} and {maximum}'

	return value, None


def switchOn():
	rgb = unicorn.hsvIntToRGB(randint(0, 360), 100, 100)
	startAnimation(setColor, (rgb[0], rgb[1], rgb[2]))


def switchOff():
	global blinkThread, globalBlue, globalGreen, globalRed
	globalRed = 0
	globalGreen = 0
	globalBlue = 0
	if blinkThread is not None:
		blinkThread.do_run = False
		if blinkThread != threading.current_thread():
			blinkThread.join(timeout=1)
		blinkThread = None
	with hardwareLock:
		unicorn.clear()
		unicorn.off()


def halfBlink():
	with hardwareLock:
		unicorn.show()
	sleep(0.8)
	with hardwareLock:
		unicorn.clear()
		unicorn.show()
	sleep(0.2)


def countDown(time):
	showTime = time - 12
	brightness = 0.5
	while showTime > 0:
		b = brightness
		for x in range(4):
			b = b - x
			setPixels(255, 255, 0, b)
			with hardwareLock:
				unicorn.show()
			sleep(0.5)
			with hardwareLock:
				unicorn.clear()
		with hardwareLock:
			unicorn.show()
		sleep(2)
		showTime = showTime - 2
	for i in range(10):
		setPixels(255, 0, 0, 0.5)
		halfBlink()
	setColor(255, 0, 0, 0.5)
	halfBlink()
	with hardwareLock:
		unicorn.clear()
		unicorn.off()


def displayRainbow(brightness, speed, run=None):
	global crntColors
	if speed is None:
		speed = 0.01
	if brightness is None:
		brightness = 0.5
	crntT = threading.current_thread()
	i = 0.0
	offset = 30
	while getattr(crntT, "do_run", True):
		i = i + 0.3
		with hardwareLock:
			unicorn.setBrightness(brightness)
			for x in range(0, width):
				for y in range(0, height):
					r = (math.cos((x + i) / 2.0) + math.cos((y + i) / 2.0)) * 64.0 + 128.0
					g = (math.sin((x + i) / 1.5) + math.sin((y + i) / 2.0)) * 64.0 + 128.0
					b = (math.sin((x + i) / 2.0) + math.cos((y + i) / 1.5)) * 64.0 + 128.0
					r = max(0, min(255, r + offset))
					g = max(0, min(255, g + offset))
					b = max(0, min(255, b + offset))
					unicorn.setPixel(x, y, int(r), int(g), int(b))

			unicorn.show()
		sleepWhileRunning(crntT, speed)


def setTimestamp():
	global globalLastCalled
	globalLastCalled = datetime.now()


# API Initialization
@app.route('/', methods=['GET'])
def root():
	print(app.static_folder)
	return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/on', methods=['GET', 'POST'])
def apiOn():
	global globalStatusOverwrite, globalStatus, globalLastCalledApi
	globalStatusOverwrite = False
	globalStatus = 'on'
	globalLastCalledApi = '/api/on'
	switchOff()
	switchOn()
	setTimestamp()
	return make_response(jsonify({}))


@app.route('/api/off', methods=['GET', 'POST'])
def apiOff():
	global crntColors, globalStatusOverwrite, globalStatus, globalLastCalledApi
	globalStatusOverwrite = False
	globalStatus = 'off'
	globalLastCalledApi = '/api/off'
	crntColors = None
	switchOff()
	setTimestamp()
	return make_response(jsonify({}))


@app.route('/api/switch', methods=['POST'])
def apiSwitch():
	global blinkThread, globalStatusOverwrite, globalStatus, globalLastCalledApi

	if globalStatusOverwrite:
		return make_response(jsonify({}))

	globalLastCalledApi = '/api/switch'
	content, error = readJsonBody()
	if error is not None:
		return error

	red, error = getNumber(content, 'red', 0, 255, True)
	if error is not None:
		return make_response(jsonify({'error': error}), 400)
	green, error = getNumber(content, 'green', 0, 255, True)
	if error is not None:
		return make_response(jsonify({'error': error}), 400)
	blue, error = getNumber(content, 'blue', 0, 255, True)
	if error is not None:
		return make_response(jsonify({'error': error}), 400)

	if red == 0 and green == 144 and blue == 0:
		globalStatus = 'Available'
	elif red == 255 and green == 191 and blue == 0:
		globalStatus = 'Away'
	elif red == 179 and green == 0 and blue == 0:
		globalStatus = 'Busy'
	elif red == 0 and green == 86 and blue == 179:
		globalStatus = 'Out of office'
	elif red == 128 and green == 128 and blue == 128:
		globalStatus = 'Appear Offline'
	elif red == 128 and green == 0 and blue == 128:
		globalStatus = 'Do not Disturb'
	else:
		globalStatus = None

	brightness, error = getNumber(content, 'brightness', 0, 1)
	if error is not None:
		return make_response(jsonify({'error': error}), 400)
	speed, error = getNumber(content, 'speed', 0.01, 60)
	if error is not None:
		return make_response(jsonify({'error': error}), 400)

	startAnimation(setColor, (int(red), int(green), int(blue), brightness, speed))
	setTimestamp()
	return make_response(jsonify())

@app.route('/api/available', methods=['GET', 'POST'])
def availableCall():
	global globalStatusOverwrite, globalStatus, globalLastCalledApi, blinkThread
	globalStatusOverwrite = True
	globalStatus = 'Available'
	globalLastCalledApi = '/api/available'
	startAnimation(setColor, (0, 144, 0))
	setTimestamp()
	return make_response(jsonify())

@app.route('/api/busy', methods=['GET', 'POST'])
def busyCall():
	global globalStatusOverwrite, globalStatus, globalLastCalledApi, blinkThread
	globalStatusOverwrite = True
	globalStatus = 'Busy'
	globalLastCalledApi = '/api/busy'
	startAnimation(setColor, (179, 0, 0))
	setTimestamp()
	return make_response(jsonify())

@app.route('/api/away', methods=['GET', 'POST'])
def awayCall():
	global globalStatusOverwrite, globalStatus, globalLastCalledApi, blinkThread
	globalStatusOverwrite = True
	globalStatus = 'Away'
	globalLastCalledApi = '/api/away'
	startAnimation(setColor, (255, 191, 0))
	setTimestamp()
	return make_response(jsonify())

@app.route('/api/out-of-office', methods=['GET', 'POST'])
def outOfOfficeCall():
	global globalStatusOverwrite, globalStatus, globalLastCalledApi, blinkThread
	globalStatusOverwrite = True
	globalStatus = 'Out of office'
	globalLastCalledApi = '/api/out-of-office'
	startAnimation(setColor, (0, 86, 179))
	setTimestamp()
	return make_response(jsonify())

@app.route('/api/appear-offline', methods=['GET', 'POST'])
def appearOfflineCall():
	global globalStatusOverwrite, globalStatus, globalLastCalledApi, blinkThread
	globalStatusOverwrite = True
	globalStatus = 'Appear Offline'
	globalLastCalledApi = '/api/appear-offline'
	startAnimation(setColor, (128, 128, 128))
	setTimestamp()
	return make_response(jsonify())

@app.route('/api/do-not-disturb', methods=['GET', 'POST'])
def doNotDisturbCall():
	global globalStatusOverwrite, globalStatus, globalLastCalledApi, blinkThread
	globalStatusOverwrite = True
	globalStatus = 'Do not Disturb'
	globalLastCalledApi = '/api/do-not-disturb'
	startAnimation(setColor, (128, 0, 128))
	setTimestamp()
	return make_response(jsonify())

@app.route('/api/reset', methods=['GET', 'POST'])
def resetCall():
	global globalStatusOverwrite, globalStatus, globalLastCalledApi, blinkThread
	globalStatusOverwrite = False
	return make_response(jsonify())


@app.route('/api/rainbow', methods=['POST'])
def apiDisplayRainbow():
	global blinkThread, globalStatus, globalLastCalledApi
	globalStatus = 'rainbow'
	globalLastCalledApi = '/api/rainbow'
	content, error = readJsonBody()
	if error is not None:
		return error

	brightness, error = getNumber(content, 'brightness', 0, 1)
	if error is not None:
		return make_response(jsonify({'error': error}), 400)
	speed, error = getNumber(content, 'speed', 0.01, 60)
	if error is not None:
		return make_response(jsonify({'error': error}), 400)

	startAnimation(displayRainbow, (brightness, speed, None))
	setTimestamp()
	return make_response(jsonify())


@app.route('/api/status', methods=['GET'])
def apiStatus():
	global globalStatusOverwrite, globalStatus, globalBlue, globalGreen, globalRed, globalBrightness, \
		globalLastCalled, globalLastCalledApi, width, height, unicorn

	try:
		cpuTemp = CPUTemperature().temperature
	except Exception:
		cpuTemp = None

	return jsonify({
		'red': globalRed, 
		'green': globalGreen,
		'blue': globalBlue,
		'brightness': globalBrightness,
		'lastCalled': globalLastCalled,
		'cpuTemp': cpuTemp,
		'lastCalledApi': globalLastCalledApi, 
		'height': height,
		'width': width,
		'unicorn': unicorn.getType(),
		'status': globalStatus,
		'statusOverwritten': globalStatusOverwrite
	})


@app.errorhandler(404)
def not_found(error):
	return make_response(jsonify({'error': 'Not found'}), 404)


def startupRainbow():
	global blinkThread
	startAnimation(displayRainbow, (1, 0.1, 1))


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=9000, debug=False)
