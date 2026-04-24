# Quick Start Guide

This guide will help you get the Harvard Ultra Multi-Pump Control application running quickly.

## Option 1: Download the Executable (Recommended for Windows)

1.  Go to the **Releases** tab in this repository.
2.  Download the latest `HarvardUltraControl-Windows-x64.exe`.
3.  Connect your Harvard Apparatus pump via a serial-to-USB adapter.
4.  Launch the executable. No installation is required.

## Option 2: Run from Source

If you prefer to run the application from source or are on a non-Windows platform:

### Prerequisites
- Python 3.10 or higher.
- A serial-to-USB adapter and appropriate drivers (e.g., FTDI).

### Installation
1.  Clone this repository:
    ```bash
    git clone https://github.com/your-username/Harvard_Pump_DIY_Control.git
    cd Harvard_Pump_DIY_Control
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run the application:
    ```bash
    python main.py
    ```

## First Steps in the App

1.  **Add a Pump:** Click **Add Pump Panel** on the dashboard.
2.  **Connect:** Select the correct COM port and address (usually `00`), then click **Connect**.
3.  **Sync Syringe:** Click **Get from Pump** to automatically load the syringe diameter currently configured on the physical pump.
4.  **Manual Test:** Enter a rate, select units, and click **Run** to verify communication.
5.  **Create a Profile:** Use the **Add Hold** or **Add Ramp** buttons to build a multi-segment profile, then click **START Profile**.

## Troubleshooting
If you encounter issues, please refer to the [Troubleshooting Guide](TROUBLESHOOTING.md).
