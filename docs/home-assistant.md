# Home Assistant Integration

Home Assistant can monitor Unicorn Solar Server with its built-in REST
integration. The sensor polls `GET /api/status`; when the HTTP endpoint is
reachable the entity state is `running`, and the API response is exposed as
sensor attributes.

The examples below intentionally use placeholder host names. Replace
`<solar-server-host>` with the hostname or IP address of the Raspberry Pi that
runs `unicorn-solar.service`.

## Enable Packages

If your Home Assistant configuration does not already load packages, add this
under `homeassistant:` in `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Then create `packages/unicorn_solar_server.yaml`:

```yaml
rest:
  - resource: http://<solar-server-host>:9001/api/status
    scan_interval: 60
    timeout: 5
    sensor:
      - name: Unicorn Solar Server
        unique_id: unicorn_solar_server_status
        value_template: "running"
        json_attributes:
          - activeBlocks
          - activeColumns
          - barColor
          - displayMode
          - flow
          - height
          - lastCalled
          - lastCalledApi
          - percentage
          - rotation
          - tariff
          - unicorn
          - width
```

Validate and restart Home Assistant after adding the package. The sensor entity
will be `sensor.unicorn_solar_server`.

`displayMode` can be `solar`, `rainbow`, `standby`, or `off`. Standby is the
intentional quiet display mode and shows a dim `HH:MM` clock on the physical
matrix.

## Dashboard Card

The visual matrix example uses
[`button-card`](https://github.com/custom-cards/button-card). Install it through
HACS or add it as a Lovelace resource before using `custom:button-card`.

```yaml
type: vertical-stack
cards:
  - type: conditional
    conditions:
      - entity: sensor.unicorn_solar_server
        state: running
    card:
      type: custom:button-card
      entity: sensor.unicorn_solar_server
      name: Unicorn Solar Server
      show_state: false
      show_icon: false
      styles:
        card:
          - padding: 16px
        name:
          - font-size: 18px
          - justify-self: start
          - margin-bottom: 12px
        custom_fields:
          matrix:
            - display: grid
            - grid-template-columns: repeat(17, 10px)
            - grid-template-rows: repeat(7, 10px)
            - gap: 3px
            - background: "#10141c"
            - padding: 10px
            - border-radius: 6px
            - width: max-content
      custom_fields:
        matrix: |
          [[[
            const attrs = entity.attributes;
            const displayMode = attrs.displayMode ?? "solar";
            const percentage = Number(attrs.percentage ?? 0);
            const activeColumns = Math.max(0, Math.min(10, Math.floor(percentage / 10)));
            const barColorName = attrs.barColor ?? "green";
            const tariff = attrs.tariff ?? "medium";

            const colors = {
              blue: "#1e78ff",
              green: "#00b450",
              red: "#e6373c",
              yellow: "#ffbe00",
              white: "#f5f8fc",
              standby: "#80beff",
              off: "#202837"
            };

            const tariffColors = {
              low: colors.green,
              medium: colors.yellow,
              high: colors.red
            };

            const digits = {
              "0": ["111", "101", "101", "101", "111"],
              "1": ["010", "110", "010", "010", "111"],
              "2": ["111", "001", "111", "100", "111"],
              "3": ["111", "001", "111", "001", "111"],
              "4": ["101", "101", "111", "001", "001"],
              "5": ["111", "100", "111", "001", "111"],
              "6": ["111", "100", "111", "101", "111"],
              "7": ["111", "001", "010", "010", "010"],
              "8": ["111", "101", "111", "101", "111"],
              "9": ["111", "101", "111", "001", "111"]
            };

            function renderDot(color) {
              return `<span style="
                width:10px;
                height:10px;
                border-radius:50%;
                background:${color};
                box-shadow:${color === colors.off ? "none" : `0 0 5px ${color}`};
                display:block;
              "></span>`;
            }

            if (displayMode === "standby") {
              const grid = Array.from({ length: 7 }, () => Array(17).fill(colors.off));
              const setPixel = (x, y, color) => {
                if (x >= 0 && x < 17 && y >= 0 && y < 7) grid[y][x] = color;
              };
              const drawDigit = (digit, xOffset) => {
                const pattern = digits[digit];
                for (let y = 0; y < 5; y++) {
                  for (let x = 0; x < 3; x++) {
                    if (pattern[y][x] === "1") setPixel(xOffset + x, y + 1, colors.standby);
                  }
                }
              };
              const now = new Date();
              const clock = `${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}`;
              drawDigit(clock[0], 0);
              drawDigit(clock[1], 4);
              setPixel(8, 2, colors.standby);
              setPixel(8, 4, colors.standby);
              drawDigit(clock[2], 10);
              drawDigit(clock[3], 14);
              return grid.flatMap(row => row.map(renderDot)).join("");
            }

            const barColor = colors[barColorName] ?? colors.green;
            const dots = [];
            const barStarts = [14, 11, 8, 5, 2];

            function isOutline(x, y) {
              return ((y === 0 || y === 6) && x >= 1) || ((x === 1 || x === 16) && y >= 1 && y <= 5);
            }

            function isTariff(x, y) {
              return x === 0 && [2, 3, 4].includes(y);
            }

            function isBatteryFill(x, y) {
              if (y < 1 || y > 5) return false;
              let remaining = activeColumns;
              for (const start of barStarts) {
                for (const col of [start + 1, start]) {
                  if (remaining <= 0) return false;
                  if (x === col) return true;
                  remaining -= 1;
                }
              }
              return false;
            }

            for (let y = 0; y < 7; y++) {
              for (let x = 0; x < 17; x++) {
                let color = colors.off;
                if (isOutline(x, y)) color = colors.white;
                if (isBatteryFill(x, y)) color = barColor;
                if (isTariff(x, y)) color = tariffColors[tariff] ?? colors.yellow;

                dots.push(renderDot(color));
              }
            }

            return dots.join("");
          ]]]

  - type: entities
    show_header_toggle: false
    entities:
      - entity: sensor.unicorn_solar_server
        name: Status

      - type: attribute
        entity: sensor.unicorn_solar_server
        attribute: percentage
        name: Battery
        suffix: "%"

      - type: attribute
        entity: sensor.unicorn_solar_server
        attribute: flow
        name: Flow

      - type: attribute
        entity: sensor.unicorn_solar_server
        attribute: barColor
        name: Bar Color

      - type: attribute
        entity: sensor.unicorn_solar_server
        attribute: tariff
        name: Tariff

      - type: attribute
        entity: sensor.unicorn_solar_server
        attribute: displayMode
        name: Display Mode

      - type: attribute
        entity: sensor.unicorn_solar_server
        attribute: lastCalled
        name: Last Called

      - type: attribute
        entity: sensor.unicorn_solar_server
        attribute: lastCalledApi
        name: Last Called API
```
