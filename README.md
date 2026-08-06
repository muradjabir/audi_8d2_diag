# Audi A4 B5 (8D2) HVAC Diagnostic Tool

A web-based diagnostic tool for the Audi A4 B5 (1994-2001) Auto HVAC (Climate Control) module over the KWP1281 protocol, using a standard KKL (FTDI) diagnostic cable.

## Features

- **Web GUI:** A modern, dark-themed automotive dashboard accessible via a web browser.
- **Port Auto-Detection:** Automatically finds your KKL/FTDI serial port.
- **Read & Clear Faults (DTCs):** Built-in database of HVAC-specific fault codes with elaboration details (Active, Intermittent, etc.).
- **Measurement Blocks:** View all sensor data (temperatures, flap positions, compressor voltages) across all 8 HVAC measurement groups.
- **Live Data Monitor:** Stream live sensor data via Server-Sent Events (SSE) with real-time sparkline charts.

## Requirements

- Python 3.9+
- A genuine FTDI FT232RL based KKL VAG-COM cable. *(Warning: Cheap clone chips often struggle with the precise 5-baud timing required to wake up the ECU).*

### Python Dependencies

```bash
pip install -r requirements.txt
```

*(This project uses only `pyserial` for hardware communication and `Flask` for the web server).*

## Usage

1. Connect your KKL cable to your vehicle's OBD-II port.
2. Turn the ignition to the ON position (engine does not need to be running, but climate control must have power).
3. Connect the KKL cable to your computer's USB port.
4. Start the server:
   ```bash
   python app.py
   ```
5. Open your web browser and navigate to `http://127.0.0.1:5000`
6. Select your port and click **Connect**.

## Safety Warning

> **CAUTION:** This tool communicates directly with vehicle electronics on the K-Line. While it is designed to be read-only (with explicit confirmation required for clearing faults), using incorrect or cheap counterfeit cables can potentially introduce noise on the K-Line or cause communication errors. Do not use this tool while the vehicle is in motion.

## Technical Details

- **Protocol:** KWP1281 (Key-Word Protocol 1281) via K-Line (ISO 9141).
- **Initialization:** 5-baud "slow init" bit-banging via standard UART Break signals.
- **Module Address:** 0x08 (Auto HVAC).
- **Communication:** Byte-level complement acknowledgement system.
