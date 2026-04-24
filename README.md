# Harvard Ultra Multi-Pump Control

A desktop control application for Harvard Apparatus PHD Ultra / Pump 11 Elite syringe pumps, with support for multiple pumps in parallel, independent COM-port control, synchronized syringe readback from the pump, manual rate control, and multi-segment profile execution.

This application is intended for laboratory use on Windows and is designed to be distributed as a standalone executable built with PyInstaller.

## Status

This repository is structured as a public-facing application repository. Before publishing, confirm that:

- all machine-specific paths, usernames, screenshots, and local-only notes have been removed,
- all default serial settings are intentional and documented,
- the release workflow has been tested on GitHub,
- the packaged `.exe` has been validated on a clean Windows machine.

## Safety notice

This software controls real hardware.

Before running any profile on a live pump:

- verify the correct COM port and pump address,
- confirm the syringe is configured correctly on the pump,
- verify units, direction, and profile durations,
- keep line-of-sight access to the pump during validation,
- confirm that Stop and Stop All behave as expected on the actual hardware,
- validate new profiles at low rates before using them in experiments.

This software does not replace local lab SOPs, instrument qualification, or operator oversight.

## What the application does

The application provides:

- multi-pump control from one desktop application,
- one independent session per pump,
- independent COM-port selection per session,
- support for pumps on separate COM ports or multiple addressed pumps on a shared daisy-chain port,
- syringe synchronization from the pump itself,
- manual rate entry and run/stop control,
- profile creation with hold and ramp segments,
- per-session live profile visualization,
- explicit stepped ramp policies,
- logging and session-level execution visibility,
- Windows executable packaging.

## Design philosophy

The pump is treated as the source of truth for syringe configuration.

Operators define the syringe on the physical pump. The application queries the pump using **Get from Pump** and displays the active syringe information inside the corresponding session panel. This avoids the need to maintain a large duplicate syringe library in software and reduces mismatch risk.

The application is organized around independent pump sessions rather than a single global device state. This makes it possible to:

- control many pumps in parallel,
- isolate faults to one session where possible,
- support both separate COM ports and daisy-chained addressed pumps,
- attach an independent profile runner to each pump.

## Feature overview

### Connection and session management

Each pump panel includes:

- COM-port selection,
- pump address field,
- Connect / Disconnect,
- syringe sync,
- manual rate and direction controls,
- profile editor,
- live chart and progress view.

A global **Stop All Pumps** action is available at the dashboard level.

### Syringe synchronization

The application reads syringe information from the pump using the command interface and displays:

- manufacturer,
- model,
- diameter.

The software does not require the syringe to be defined in advance when the operator has already configured it on the pump.

### Manual control

Each session supports:

- setting a flow rate,
- selecting units,
- setting direction,
- starting infusion or withdrawal,
- stopping,
- refreshing current status and rate.

### Profile engine

The profile engine currently supports:

- Hold segments,
- Ramp segments,
- multi-step profiles,
- per-session execution,
- per-session progress,
- per-session live charting.

### Live charting

The profile view shows both:

- the **Ideal Profile**: the mathematically continuous target profile,
- the **Actual Commanded Setpoint**: the staircase of rate commands actually acknowledged by the pump.

This distinction is important. The stepped trace is the command history sent to the pump, not a direct measurement of physical fluid output.

### Ramp policies

The application supports explicit stepped ramp policies such as:

- stepped fine,
- stepped adaptive,
- stepped coarse,
- custom.

The active policy determines:

- update interval,
- minimum rate delta,
- maximum command frequency,
- maximum divergence from ideal.

These controls balance command traffic, audible command acknowledgement behavior, and closeness to the ideal ramp.

## Repository layout

Example public structure:

```text
.
├── refactored_pump_control/
│   ├── __init__.py
│   ├── chart_widget.py
│   ├── harvard_ultra_driver.py
│   ├── main_window.py
│   ├── profile_model.py
│   ├── profile_runner.py
│   ├── pump_driver_base.py
│   ├── pump_panel_widget.py
│   ├── pump_session.py
│   ├── serial_transport.py
│   └── transport_manager.py
├── main.py
├── requirements.txt
├── HarvardUltraControl.spec
├── README.md
├── LICENSE
└── .github/
    └── workflows/
        └── release.yml
```

## Architecture

### 1. Main window and dashboard

`main_window.py` owns the application shell and dashboard.

Responsibilities:

- application-level layout,
- Add Pump Panel action,
- Stop All Pumps action,
- lifecycle of visible pump panels.

### 2. Pump panel widget

`pump_panel_widget.py` provides the operator-facing UI for one pump session.

Responsibilities:

- connection controls,
- syringe sync controls,
- manual control actions,
- profile editor,
- ramp policy controls,
- save/load profile actions,
- live chart integration,
- session signal wiring.

### 3. Pump session

`pump_session.py` is the control boundary for one physical/logical pump.

Responsibilities:

- session state,
- transport association,
- driver ownership,
- syringe info cache,
- session log,
- start/stop/pause/resume of per-session profile execution,
- UI-safe signal emission.

### 4. Transport manager

`transport_manager.py` shares transports by COM port.

This matters because two deployment modes are possible:

- one pump per COM port,
- multiple addressed pumps sharing one daisy-chained COM port.

When multiple sessions share a port, they must share the same `SerialTransport` so serial IO remains serialized correctly on the wire.

### 5. Serial transport

`serial_transport.py` owns low-level serial communication.

Responsibilities:

- opening and closing the serial port,
- transport-level locking,
- request/response transactions,
- prompt-based reads for acknowledgement-style commands,
- CR-based reads for query-style commands,
- low-level logging and timing.

### 6. Pump driver

`harvard_ultra_driver.py` implements the Harvard Ultra / Pump 11 Elite command layer.

Responsibilities:

- address formatting,
- mapping application operations to pump commands,
- connection verification,
- status parsing,
- syringe information queries,
- rate set/get commands,
- run and stop commands.

The driver is separated from the transport so future pump variants or protocol modes can be added cleanly.

### 7. Profile model

`profile_model.py` defines profile data structures.

Responsibilities:

- ramp and hold segment data,
- serialization to and from JSON,
- total duration calculation,
- ideal-rate evaluation over time,
- ramp-policy persistence.

### 8. Profile runner

`profile_runner.py` executes one profile for one session.

Responsibilities:

- per-session background execution,
- monotonic timing,
- stepped ramp approximation,
- command throttling,
- divergence-based updates,
- progress signals,
- completion and abort handling.

### 9. Chart widget

`chart_widget.py` renders the live execution graph.

Responsibilities:

- draw ideal profile trace,
- draw actual commanded staircase,
- draw live execution cursor,
- update in real time from session signals.

## Serial communication model

The pump protocol uses a mix of response styles:

- some commands return prompt-only acknowledgements,
- some queries return data terminated by carriage return.

The transport/driver split should therefore support at least two read modes:

- prompt-based read for acknowledgement commands,
- CR-based read for query commands.

This separation is important for latency, because prompt-only acknowledgements should not wait for a timeout that was intended for CR-terminated data responses.

## Build and run locally

### Prerequisites

- Python 3.10+ or the version pinned by the repository
- Windows recommended for hardware use and packaging
- Harvard Ultra or Pump 11 Elite connected by serial/USB-serial adapter
- PyQt5 and other dependencies from `requirements.txt`

### Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Run from source

```bash
python main.py
```


## Acknowledgements

This project owes a clear debt to the original **HarvardPumps_Python3** package and related prior work. The earlier package provided useful guidance, inspiration, and protocol information that helped shape this refactor and the public-facing application architecture.

Thank you to the authors and maintainers of that earlier package for the foundation it provided.