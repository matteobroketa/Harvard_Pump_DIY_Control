# Troubleshooting Guide

This guide addresses common issues with the Harvard Ultra Multi-Pump Control application.

## Connection Issues

### Pump does not verify on connect
- **Check the physical connection:** Ensure the USB-serial adapter is fully plugged in and recognized by your OS.
- **Identify the correct COM port:** Use Device Manager (Windows) or `ls /dev/tty.*` (macOS/Linux) to find the correct port.
- **Baud Rate/Framing:** Ensure the pump's serial settings match the application defaults (usually 115200 baud, 8 data bits, 1 stop bit, no parity).
- **Correct Address:** The default address is usually `00`. If you have daisy-chained pumps, each must have a unique address (e.g., `01`, `02`).
- **Command Mode:** Ensure the pump is in the correct command mode (usually "Protocol" or "Advanced" mode, not standard mode).

### Serial port is already in use
- Only one session in the application can claim a specific COM port. If you have multiple sessions sharing a port, ensure they are using different addresses on the same transport.
- Close other software (e.g., PuTTY, LabVIEW, or old instances of the pump control software) that might be holding the port open.

## Communication/Behavioral Issues

### Commands appear slow or laggy
- High-frequency status polling or excessive profile updates can saturate the serial link.
- If you are daisy-chaining multiple pumps on one port, reduce the "Max Hz" in the Ramp Policy to reduce traffic.

### The pump does not start when I click "Run"
- Ensure the pump is not in an error state.
- Check the manual rate and direction settings. If the rate is too low or invalid, the pump may reject the run command.
- Try a "Refresh" to see the current state reported by the pump.

### "Get from Pump" fails
- This query requires the pump to be connected and responsive. Verify connection first.
- Ensure your pump model supports the `diameter` query (Harvard Ultra and Pump 11 Elite series do; older models may not).

## Profile Execution Issues

### Profile ramps look like "staircases"
- This is intentional behavior for stepped ramps. The application approximates a continuous ramp by sending discrete rate updates at a high frequency.
- You can adjust the "fineness" of the staircase by selecting a different **Ramp Policy** (e.g., "Stepped Fine").

### The profile stopped unexpectedly
- Check for hardware-level stops (e.g., force limit reached, end of travel).
- Look at the per-session log to see if a command failed or was rejected by the pump.

## Application Crashes

- **Log File:** The application outputs debug logs to the console/terminal. If you are running from the `.exe` and it crashes, try running from source (`python main.py`) to capture the error trace.
- **Reporting:** Please include the specific pump model, connection type, and any error messages from the log when seeking assistance.
