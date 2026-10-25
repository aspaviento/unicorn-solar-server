# Scheduling the panel with cron

For an unattended Linux installation, the recommended approach is to use cron
to run a small controller script that sends updates to Unicorn Solar Server's
HTTP API. The service handles drawing; your controller decides when to show
solar information and when to show the dim standby clock.

This is optional. You can also drive the API manually, from Home Assistant,
or from another scheduler. The installer does not add cron entries.

The [example shell script](../examples/cron/panel-cron.sh) and its
[mock inputs](../examples/cron/mock-data/) demonstrate the complete cycle.
All dates, times, battery values, tariff levels, and paths in this example are
fictional or generic. It needs no cloud account or credentials.

## 1. Understand who controls each behavior

| Behavior | Owner |
| --- | --- |
| Obtain current battery/energy data | Your data-provider integration or script |
| Obtain sunrise/sunset for the current date and location | Your weather/astronomical data provider |
| Classify the current tariff as low/medium/high | Your tariff integration or script |
| Decide between solar display and standby clock | The cron controller below |
| Render battery, tariff, or clock | Unicorn Solar Server |
| Change white/violet outline for optional consumption windows | The server's internal schedule monitor |

The server does **not** calculate sunrise/sunset, retrieve your battery state,
or schedule night mode automatically. The web panel's consumption windows are
a separate optional indication; they do not control the daylight period.

The controller uses one shared daylight gate:

```text
Outside [sunrise, sunset): POST /api/standby, then stop
Inside  [sunrise, sunset): POST /api/battery, then POST /api/tariff
```

**Any battery, SolarEdge, or tariff update exits standby.** Never let a separate
nighttime tariff job wake the display: either use the single controller or
apply the same daylight gate to every producer that posts to the panel.
Repeated standby requests are idempotent. Use `/api/standby` for a visible dim
clock; `/api/off` intentionally blanks every pixel.

## 2. Install and copy the example

On Debian/Raspberry Pi OS, install the example's prerequisites if needed:

```bash
sudo apt install cron curl jq python3 util-linux tzdata
```

Python 3.9+ supplies `zoneinfo`; `util-linux` supplies `flock`. The script uses
only the standard Python library, so it does not require the server's virtual
environment or additional Python packages.

From the project checkout, copy the example to a separate working directory:

```bash
mkdir -p "$HOME/.local/share/unicorn-solar-cron"
cp -R examples/cron/. "$HOME/.local/share/unicorn-solar-cron/"
chmod +x "$HOME/.local/share/unicorn-solar-cron/panel-cron.sh"
mkdir -p "$HOME/.local/state/unicorn-solar-cron"
```

Use absolute paths in scheduled commands. Keep runtime input files outside
the source repository when replacing the demonstration with real data.

## 3. Try fictional daytime and nighttime without touching the display

The supplied daylight fixture is deliberately dated **2030-06-01**, in
`Etc/UTC`, with sunrise 07:30 and sunset 20:30. It is not a real astronomical
forecast. Run the same script at two simulated instants:

```bash
"$HOME/.local/share/unicorn-solar-cron/panel-cron.sh" --dry-run --at 2030-06-01T12:00:00+00:00
"$HOME/.local/share/unicorn-solar-cron/panel-cron.sh" --dry-run --at 2030-06-01T22:00:00+00:00
```

The first prints the two proposed daytime requests:

```text
POST /api/battery {"percentage":60,"flow":"charging"}
POST /api/tariff {"level":"medium"}
```

The second prints only:

```text
POST /api/standby {}
```

The default is `--dry-run`: no HTTP request is sent. `--at` requires an explicit
UTC offset and cannot be combined with `--apply`, so a simulated date cannot
accidentally govern a real panel. Omit `--at` to evaluate the actual current time.

## 4. Supply current inputs

Configure these environment variables, either in your shell for manual runs
or in your crontab for scheduled runs:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PANEL_API_URL` | `http://127.0.0.1:9001` | Panel API on the same machine; change if the controller runs elsewhere |
| `PANEL_TIMEZONE` | `Etc/UTC` | IANA zone used to interpret the daylight date and times |
| `DATA_DIR` | `mock-data` next to the script | Directory containing the three JSON inputs |

Use your actual IANA zone. Align the Raspberry Pi system time zone as well:
the standby clock uses the service host's local time. The optional consumption
window configuration has its own time-zone field; choose the intended zone
there too. IANA conversion follows seasonal UTC-offset changes automatically;
refresh sunrise/sunset every day rather than applying a permanent one-hour shift.

The three input files are:

```json
// daylight.json — replace with today's local date and actual sunrise/sunset
{"date": "2030-06-01", "sunrise": "07:30", "sunset": "20:30"}

// battery.json — replace with current battery state
{"percentage": 60, "flow": "charging"}

// tariff.json — replace with the current tariff classification
{"level": "medium"}
```

The comment lines above label the examples; do not put comments in the actual
JSON files. `flow` accepts `charging`, `discharging`, or `exporting` (the last
requires 100% for `/api/battery`); `level` accepts `low`, `medium`, or `high`.

For real operation, replace the fixtures with outputs from your own providers.
Refresh daylight data daily and battery/tariff data at suitable intervals for
their sources. Write complete files atomically, for example by writing a
temporary file in the same directory and renaming it. Keep tokens and account
identifiers in private provider configuration, not in the controller or cron.
Do not commit real payloads, locations, or credentials to this repository.

The example intentionally does not retrieve cloud data or model a real tariff.
A production adapter must check source freshness; a successful POST only proves
that the server accepted a payload, not that its underlying measurement is new.
If adapting the controller to fetch solar data itself, keep that query **after**
the daylight gate to avoid querying the provider at night.

SolarEdge users may instead send the provider's current-power-flow JSON to
[`/api/solaredge-interface`](../README.md#update-from-solaredge-interface).
Adapt both payload validation and the daytime battery POST together, retaining
the same daylight gate and tariff protection.

Missing, malformed, or wrong-date daylight data makes the example exit with an
error **without changing the panel**. It does not invent sunrise/sunset or
silently fall back to fixed hours. Inspect failures and fix the upstream feed;
the previous display mode may otherwise remain visible. This example assumes
a normal local date with sunrise before sunset; polar day/night needs a
separate policy. Night mode does not require battery or tariff files.

## 5. Verify manually before scheduling

After supplying current data and setting the intended environment, inspect:

```bash
"$HOME/.local/share/unicorn-solar-cron/panel-cron.sh" --dry-run
```

When the proposed request is correct, explicitly allow it to change the panel:

```bash
"$HOME/.local/share/unicorn-solar-cron/panel-cron.sh" --apply
curl --fail --silent http://127.0.0.1:9001/api/status
```

Expect `displayMode: solar` during the active period and `displayMode: standby`
outside it. The schedule monitor may change the outline in solar mode, but
never interrupts standby. `highConsumptionExpected` can still be true while
the physical panel is showing its clock.

## 6. Add an example crontab entry

Run `crontab -e` as the controller's normal user and **add** the following to
existing entries after adjusting the zone, URL, paths, and cadence:

```cron
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
PANEL_TIMEZONE=Etc/UTC
PANEL_API_URL=http://127.0.0.1:9001

*/5 * * * * "$HOME/.local/share/unicorn-solar-cron/panel-cron.sh" --apply > "$HOME/.local/state/unicorn-solar-cron/panel.log" 2>&1
```

Do not replace an existing crontab. `SHELL`/`PATH` affect subsequent entries;
merge these settings with your existing configuration. Ensure cron is running
and verify the result with `crontab -l`. The script needs write access to
`DATA_DIR` for its overlap-prevention lock and to the log directory.

The cadence is an example: with a five-minute interval, clock/daylight
transitions can take up to approximately five minutes. Use a one-minute
interval if that precision is needed. Local API updates do not require cloud
queries every minute: schedule provider refreshes separately, within their
quotas. The server's optional violet-outline transitions still run internally
every second, independently of this cron interval.

Cron owns stdout/stderr redirection; the script does not write its own logs.
`>` keeps the latest invocation. Inspect failures and use an appropriate log
rotation strategy if changing this to append. Overlapping runs sharing the
same `DATA_DIR` are skipped through `flock`.

This controller intentionally owns the scheduled display: a manual off or
rainbow selection will be replaced by the next cron run. For a lasting manual
override, pause that controller first. After a service restart, the next
successful invocation replaces startup rainbow with the appropriate mode.
