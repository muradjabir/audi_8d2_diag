# meas_decoder.py
# KWP1281 Measuring Block Value Formulas
# Reference: http://nefariousmotorsports.com/forum/index.php?topic=22.0
# Formula IDs are DECIMAL (1-70), matching the first byte in each 3-byte measurement triplet.

def decode_measurement(formula: int, a: int, b: int) -> dict:
    val = 0.0
    unit = ""
    raw = f"0x{formula:02X}, {a}, {b}"
    
    try:
        if formula == 1:
            val = a * 0.2 * b
            unit = "RPM"
        elif formula == 2:
            val = a * 0.002 * b
            unit = "%"
        elif formula == 3:
            val = a * 0.002 * b
            unit = "°"
        elif formula == 4:
            val = abs(b - 127) * 0.01 * a
            unit = "°ATDC" if b > 127 else "°BTDC"
        elif formula == 5:
            val = 0.1 * a * b - 10 * a
            unit = "°C"
        elif formula == 6:
            val = 0.001 * a * b
            unit = "V"
        elif formula == 7:
            val = 0.01 * a * b
            unit = "km/h"
        elif formula == 8:
            val = 0.1 * a * b
            unit = ""
        elif formula == 9:
            val = (b - 127) * 0.02 * a
            unit = "°"
        elif formula == 10:
            val = b
            unit = "COLD" if b == 0 else "WARM"
        elif formula == 11:
            val = 0.0001 * a * (b - 128) + 1
            unit = ""
        elif formula == 12:
            val = 0.001 * a * b
            unit = "Ω"
        elif formula == 13:
            val = (b - 127) * 0.001 * a
            unit = "mm"
        elif formula == 14:
            val = 0.005 * a * b
            unit = "bar"
        elif formula == 15:
            val = 0.01 * a * b
            unit = "ms"
        elif formula == 16:
            # Bitfield: b = bit flags, a = bitmask of which bits are used
            val = b
            unit = "Bits"
        elif formula == 17:
            # Two ASCII characters
            val = 0
            unit = chr(a) + chr(b) if 32 <= a <= 126 and 32 <= b <= 126 else f"{a:02X}{b:02X}"
        elif formula == 18:
            val = 0.04 * a * b
            unit = "mbar"
        elif formula == 19:
            val = a * b * 0.01
            unit = "L"
        elif formula == 20:
            val = a * (b - 128) / 128
            unit = "%"
        elif formula == 21:
            val = 0.001 * a * b
            unit = "V"
        elif formula == 22:
            val = 0.001 * a * b
            unit = "ms"
        elif formula == 23:
            val = (b / 256) * a
            unit = "%"
        elif formula == 24:
            val = 0.001 * a * b
            unit = "A"
        elif formula == 25:
            val = (b * 1.421) + (a / 182)
            unit = "g/s"
        elif formula == 26:
            val = b - a
            unit = "°C"
        elif formula == 27:
            val = abs(b - 128) * 0.01 * a
            unit = "°ATDC" if b < 128 else "°BTDC"
        elif formula == 28:
            val = b - a
            unit = ""
        elif formula == 29:
            val = 0
            unit = "Map 1" if b < a else "Map 2"
        elif formula == 30:
            val = (b / 12) * a
            unit = "°C kW"
        elif formula == 31:
            val = (b / 2560) * a
            unit = "°C"
        elif formula == 32:
            val = (b - 256) if b > 128 else b
            unit = ""
        elif formula == 33:
            val = (100 * b / a) if a != 0 else (100 * b)
            unit = "%"
        elif formula == 34:
            val = (b - 128) * 0.01 * a
            unit = "kW"
        elif formula == 35:
            val = 0.01 * a * b
            unit = "L/h"
        elif formula == 36:
            val = b * 10 + a * 2560
            unit = "km"
        elif formula == 37:
            val = (a << 8) | b  # Unknown formula, show raw
            unit = "raw"
        elif formula == 38:
            val = (b - 128) * 0.001 * a
            unit = "°C kW"
        elif formula == 39:
            val = (b / 256) * a
            unit = "mg/h"
        elif formula == 40:
            val = b * 0.1 + (25.5 * a) - 400
            unit = "A"
        elif formula == 41:
            val = b + a * 255
            unit = "Ah"
        elif formula == 42:
            val = b * 0.1 + (25.5 * a) - 400
            unit = "kW"
        elif formula == 43:
            val = b * 0.1 + (25.5 * a)
            unit = "V"
        elif formula == 44:
            # Time display
            val = 0
            unit = f"{a}:{b:02d}"
        elif formula == 45:
            val = 0.1 * a * b / 100
            unit = ""
        elif formula == 46:
            val = (a * b - 3200) * 0.0027
            unit = "°C kW"
        elif formula == 47:
            val = (b - 128) * a
            unit = "ms"
        elif formula == 48:
            val = b + a * 255
            unit = ""
        elif formula == 49:
            val = (b / 4) * a
            unit = "mg/h"
        elif formula == 50:
            val = ((b - 128) / (0.01 * a)) if a != 0 else ((b - 128) / 0.01)
            unit = "mbar"
        elif formula == 51:
            val = ((b - 128) / 255) * a
            unit = "mg/h"
        elif formula == 52:
            val = b * 0.02 * a - a
            unit = "Nm"
        elif formula == 53:
            val = (b - 128) * 1.4222 + 0.006 * a
            unit = "g/s"
        elif formula == 54:
            val = a * 256 + b
            unit = ""
        elif formula == 55:
            val = a * b / 200
            unit = "s"
        elif formula == 56:
            val = a * 256 + b
            unit = "WSC"
        elif formula == 57:
            val = a * 256 + b + 65536
            unit = "WSC"
        elif formula == 58:
            val = 1.0225 * (256 - b) if b > 128 else 1.0225 * b
            unit = ""
        elif formula == 59:
            val = (a * 256 + b) / 32768
            unit = ""
        elif formula == 60:
            val = (a * 256 + b) * 0.01
            unit = "s"
        elif formula == 61:
            val = ((b - 128) / a) if a != 0 else (b - 128)
            unit = ""
        elif formula == 62:
            val = 0.256 * a * b
            unit = "S"
        elif formula == 63:
            # ASCII + "?"
            val = 0
            unit = (chr(a) if 32 <= a <= 126 else "?") + (chr(b) if 32 <= b <= 126 else "?") + "?"
        elif formula == 64:
            val = a + b
            unit = "Ω"
        elif formula == 65:
            val = 0.01 * a * (b - 127)
            unit = "mm"
        elif formula == 66:
            val = (a * b) / 511.12
            unit = "V"
        elif formula == 67:
            val = (640 * a) + b * 2.5
            unit = "°"
        elif formula == 68:
            val = (256 * a + b) / 7.365
            unit = "°/s"
        elif formula == 69:
            val = (256 * a + b) * 0.3254
            unit = "bar"
        elif formula == 70:
            val = (256 * a + b) * 0.192
            unit = "m/s²"
        else:
            val = (a << 8) | b  # Fallback raw value
            unit = "raw"
            
    except Exception as e:
        val = 0
        unit = "Err"
        
    # Round to 2 decimal places if it's a float
    if isinstance(val, float):
        val = round(val, 2)
        
    return {
        "value": val,
        "unit": unit,
        "raw": raw,
        "formula_id": formula,
        "a": a,
        "b": b
    }
