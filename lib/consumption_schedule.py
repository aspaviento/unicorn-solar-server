"""Persistent daily consumption windows; independent of solar telemetry."""
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_SETTINGS = {'windows': '', 'timezone': 'Europe/Madrid'}
VIOLET = (191, 112, 255)


def settings_path():
    configured = os.getenv('UNICORN_SOLAR_SETTINGS_PATH')
    if configured:
        return Path(configured).expanduser()
    return Path(os.getenv('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'unicorn-solar-server/settings.json'


def validate_settings(value):
    if not isinstance(value, dict):
        raise ValueError('Settings must be an object')
    windows = value.get('windows')
    tz = value.get('timezone')
    if not isinstance(windows, str) or len(windows) > 2048:
        raise ValueError('windows must be a string of at most 2048 characters')
    if not isinstance(tz, str) or not tz:
        raise ValueError('timezone must be an IANA timezone')
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('timezone must be a valid IANA timezone') from None
    normalized = []
    for item in windows.split(',') if windows.strip() else []:
        item = item.strip()
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d-(?:[01]\d|2[0-3]):[0-5]\d', item):
            raise ValueError('Use comma-separated HH:MM-HH:MM windows')
        start, end = item.split('-')
        if start == end:
            raise ValueError('Window start and end must differ')
        normalized.append(item)
    return {'windows': ','.join(normalized), 'timezone': tz}


def load_settings():
    try:
        return validate_settings(json.loads(settings_path().read_text()))
    except FileNotFoundError:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    """Replace atomically; preserve the last valid file on write failure."""
    target = settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=target.parent, delete=False) as stream:
            temporary = stream.name
            json.dump(settings, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def is_active(settings, now=None):
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(settings['timezone']))
    current = local.hour * 60 + local.minute
    for item in settings['windows'].split(',') if settings['windows'] else []:
        start, end = (int(t[:2]) * 60 + int(t[3:]) for t in item.split('-'))
        inside = start <= current < end if start < end else current >= start or current < end
        if inside:
            return True
    return False
