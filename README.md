# Unicorn Solar Server

Display the battery, energy flow, and current electricity tariff of a domestic
solar installation on a Raspberry Pi with a Pimoroni Unicorn HAT Mini.

The project provides:

- A 17x7 battery display designed for Unicorn HAT Mini.
- A validated HTTP API for external solar-monitoring scripts.
- A responsive React control panel with a simulated matrix preview.
- Built-in API documentation.
- A systemd service and Raspberry Pi installation scripts.
- A hardware-free dummy mode for local development and automated tests.

![Unicorn Solar Server control panel](./assets/frontend.jpg)

## Project lineage

Unicorn Solar Server is derived from
[aspaviento/unicorn-busy-server](https://github.com/aspaviento/unicorn-busy-server),
which is itself based on
[estruyf/unicorn-busy-server](https://github.com/estruyf/unicorn-busy-server).

The derived project reuses the Flask/Vite structure and Unicorn hardware
wrapper, but replaces the busy-light behavior with a solar battery display and
a dedicated API. It was developed with assistance from OpenAI Codex.

## Display

The server requires the Unicorn HAT Mini's native 17x7 orientation. It sets
rotation `0` and refuses to start with a different display shape so the battery
cannot be silently cropped or rotated.

- White pixels form the battery outline.
- Five inner bars represent battery percentage in 20% steps, filling from
  right to left.
- `0%` lights no bars.
- `1-20%`, `21-40%`, `41-60%`, `61-80%`, and `81-100%` light one through five
  bars respectively.
- Green bars mean charging.
- Red bars mean discharging.
- Blue bars mean exporting surplus energy. Exporting is accepted only at
  `100%`.
- The three-pixel battery terminal represents the electricity tariff: green
  for low, yellow for medium, and red for high.

## API

### Update battery

```http
POST /api/battery
Content-Type: application/json

{"percentage": 65, "flow": "charging"}
```

`percentage` accepts any number from `0` to `100`. `flow` accepts `charging`,
`discharging`, or `exporting`.

### Update tariff

```http
POST /api/tariff
Content-Type: application/json

{"level": "low"}
```

`level` accepts `low`, `medium`, or `high`.

### Read status

```http
GET /api/status
```

The response includes the current solar state, active bars, hardware type,
display dimensions, and rotation.

## Installation

The installer supports Raspberry Pi OS and Ubuntu:

```bash
curl -LSs https://raw.githubusercontent.com/aspaviento/unicorn-solar-server/master/install.sh | sudo bash -
```

Solar Server is installed as `unicorn-solar.service` and listens on port
`9001`.

```bash
systemctl status unicorn-solar.service
```

Open the control panel at:

```text
http://<raspberry-pi-ip>:9001/
```

## Coexisting with Unicorn Busy Server

Both projects can be installed on the same Raspberry Pi:

| Project | systemd service | HTTP port |
|---|---|---:|
| Unicorn Busy Server | `busylight.service` | `9000` |
| Unicorn Solar Server | `unicorn-solar.service` | `9001` |

Only one service should control the Unicorn HAT Mini at a time. Solar Server's
systemd unit conflicts with `busylight.service`, so starting Solar Server stops
Busy Server. The installer also disables Busy Server to ensure Solar Server
remains the selected service after a reboot.

Activate Solar Server:

```bash
sudo systemctl disable --now busylight.service
sudo systemctl enable --now unicorn-solar.service
```

Return to Busy Server:

```bash
sudo systemctl disable --now unicorn-solar.service
sudo systemctl enable --now busylight.service
```

## Development

Create a Python environment and run the server:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install flask flask-cors jsmin
.venv/bin/python server.py
```

Without compatible hardware, the wrapper automatically uses a 17x7 dummy
display. The server and control panel are available at
`http://localhost:9001/`.

Build the frontend:

```bash
cd frontend
npm install
npm run build
```

All user-facing frontend labels and descriptions are centralized in
`frontend/src/content.ts`.

Run the backend tests:

```bash
.venv/bin/python -m unittest -v
```

## License

Licensed under the MIT License. See [LICENSE](./LICENSE).
