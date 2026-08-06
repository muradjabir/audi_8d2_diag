# ecu_defs.py

HVAC_ADDRESS = 0x08

# Measuring block definitions for 8L0 820 043 E
# These labels are based on the actual formula IDs and data patterns observed from the ECU.
HVAC_GROUPS = {
    1: {
        "name": "Compressor & Blower Status",
        "fields": ["Compressor Shut-off Code", "Target Blower Voltage",
                   "System Voltage", "Blower Status/Duty"]
    },
    2: {
        "name": "Temperature Sensors (Raw)",
        "fields": ["Interior Sensor (G56) ADC", "Dash Sensor (G86) ADC",
                   "Fresh Air Sensor (G89) ADC", "Set Temperature (Raw)"]
    },
    3: {
        "name": "External Sensors (Raw)",
        "fields": ["Outside Air Sensor (G17) ADC", "Evaporator Sensor (G263) ADC",
                   "Coolant Temp ADC", "Sunlight Sensor (G107) ADC"]
    },
    4: {
        "name": "Temp Regulator Flap",
        "fields": ["V68 Position (G92)", "V68 Target Position",
                   "V68 Motor Power", "V68 Deviation"]
    },
    5: {
        "name": "Central Flap",
        "fields": ["V70 Position (G112)", "V70 Target Position",
                   "V70 Motor Power", "V70 Deviation"]
    },
    6: {
        "name": "Footwell/Defroster Temps",
        "fields": ["Vent Temp 1", "Vent Temp 2",
                   "Vent Temp 3 (-49C = Open/Disconnected)", "Flap Deviation"]
    },
    7: {
        "name": "Air Flow Temps",
        "fields": ["Vent Temp 1", "Vent Temp 2",
                   "Vent Temp 3 (-49C = Open/Disconnected)", "Unknown Status"]
    },
    8: {
        "name": "Sensor Voltages",
        "fields": ["Voltage 1", "Voltage 2",
                   "Voltage 3", "Voltage 4"]
    },
}
