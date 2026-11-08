# Changelog

Release notes describe changes to Unicorn Solar Server. Household deployment
configuration is not part of this repository.

## [1.3.0] - 2026-11-08

### Added

- Orange battery outline when measured household power reaches the configurable
  threshold, 3000 W by default. Scheduled periods retain the violet outline
  when measured high consumption is inactive.
- Optional cyan EV charging pixel in the lower-left corner of the solar view.
  The standby clock continues to show the connectivity indicator.
- Optional `householdPowerW` and `evCharging` fields on the SolarEdge update
  endpoint, with status reporting and configuration in the web panel.

## [1.2.0] - 2026-11-08

### Added

- Loopback-only `POST /api/connectivity` for local watchdog reports and a
  `connectivity` field in the status API.
- A steady connectivity pixel in the top-left corner of the daytime matrix
  and standby clock. Green shows gateway reachability, orange shows a retry
  or recovery in progress, and red shows failed recovery.
- Home Assistant REST sensor and dashboard examples for the connectivity pixel.

### Changed

- Trimmed the two left corners of the battery outline to separate the
  connectivity pixel from the battery while preserving the tariff indicator.

## [1.1.0] — 2026-10-25

This release collects the functionality added since the first public release,
with additive API features and improved installation and integration guidance.

### Added

- SolarEdge current-power-flow JSON support through
  `/api/solaredge-interface` and a dedicated form in the web panel, compatible
  with output from `ndejong/solaredge-interface`.
- Startup rainbow and API/web controls for hardware validation and full off.
- A distinct, idempotent `/api/standby` mode with a dim `HH:MM` clock. Battery
  or tariff updates resume the solar display.
- Optional daily expected high-consumption periods with a violet battery
  outline, configurable in the web panel or `/api/settings`. Settings persist
  outside the source checkout; IANA time zones handle daylight saving changes.
  The indication is disabled when no windows are configured and respects
  standby, off, and rainbow modes.
- Home Assistant REST sensor and dashboard examples, including display mode
  and the optional expected-consumption indication.
- A step-by-step cron-controller guide with a shell script, fictional JSON
  fixtures, dry-run simulation, and a shared daylight gate that prevents
  nighttime updates from interrupting the standby clock.
- A security policy describing supported releases and private reporting.

### Changed

- Battery fill now advances in 10% column steps instead of the initial 20%
  whole-block steps. Levels 0–9% light no inner columns; each additional 10%
  lights one column while retaining the native 17x7 layout.
- Raspberry Pi installation creates an isolated Python virtual environment,
  installs application dependencies into it, and supports explicit service
  user and environment paths. Runtime no longer relies on system Flask
  packages through `--system-site-packages`.
- Clarified how to update a deployment copy when the runtime directory is not
  a Git checkout, with public code separated from private operating details.
- Aligned the private frontend package metadata with the project release.

### Fixed

- Corrected the column fill order within battery blocks.
- Limited `UNICORN_FORCE_DUMMY=1` to automatic hardware selection, preserving
  explicit device choices used by hardware-wrapper tests.

### Compatibility and upgrading

Existing battery and tariff API callers remain supported. New settings and
status fields are additive. Battery visualization uses the revised 10% steps
above. Users adopting the updated Home Assistant example should add the new
attributes to their own configuration as needed.

Publishing this release does not update an existing installation. Deploy the
validated source and bundled frontend deliberately; restart the service when
updating server code. Review the isolated-environment installation guidance
when upgrading an older installation. Preserve the service user's separate
settings file. The cron example remains opt-in and is not installed by the
application installer.

## [1.0.0] — 2026-06-06

Initial public release of Unicorn Solar Server, derived from Unicorn Busy
Server:

- Native Unicorn HAT Mini 17x7 battery visualization, flow colors, and tariff
  terminal.
- Battery, tariff, status, and endpoint-discovery HTTP APIs.
- React control panel with simulated matrix preview and API documentation.
- Raspberry Pi installation scripts, systemd service, and dummy-hardware tests.

[1.1.0]: https://github.com/aspaviento/unicorn-solar-server/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/aspaviento/unicorn-solar-server/releases/tag/v1.0.0

[1.2.0]: https://github.com/aspaviento/unicorn-solar-server/releases/tag/v1.2.0

[1.3.0]: https://github.com/aspaviento/unicorn-solar-server/releases/tag/v1.3.0
