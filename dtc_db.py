# dtc_db.py

HVAC_DTC_DATABASE = {
    # === Temperature Sensors ===
    "00785": "Temperature Sensor in Instrument Panel (G56)",
    "00779": "Outside Air Temperature Sensor (G17)",
    "00797": "Sunlight Photo Sensor (G107)",
    "00256": "A/C Pressure/Temperature Sensor (G395) - No Signal",
    "00258": "Interior Temp Sensor (G56) - Open/Short",
    "00259": "Interior Temp Sensor (G56) - Signal Out of Range",
    "00260": "Outside Temp Sensor (G17) - Open/Short",
    "00261": "Outside Temp Sensor (G17) - Signal Out of Range",
    "00262": "Dashboard Temp Sensor (G86) - Open/Short",
    "00263": "Fresh Air Intake Temp Sensor (G89) - Open/Short",
    "00818": "Evaporator Outlet Temp Sensor (G263) - Open/Short",
    "00819": "A/C High Pressure Sensor (G65) - Signal Too Low",
    "00820": "A/C High Pressure Sensor (G65) - Signal Too High",
    
    # === Flap Positioning Motors ===
    "01272": "Central Flap Positioning Motor (V70) - Fault",
    "01273": "Central Flap Potentiometer (G112) - Open/Short",
    "01274": "Air Flow Flap Positioning Motor (V71) - Fault",
    "01275": "Air Flow Flap Potentiometer (G113) - Open/Short",
    "01276": "Footwell/Defroster Flap Motor (V68) - Fault",
    "01277": "Footwell/Defroster Potentiometer (G114) - Open/Short",
    "01278": "Temp Regulator Flap Motor (V68) - Fault",
    "01279": "Temp Regulator Potentiometer (G92) - Open/Short",
    
    # === Compressor & Pressure ===
    "00816": "A/C Compressor Control - Open Circuit",
    "00817": "A/C Compressor Clutch (N25) - Short to Ground",
    "01206": "A/C Refrigerant Pressure Too High",
    "01207": "A/C Refrigerant Pressure Too Low",
    
    # === Blower & Electrical ===
    "00898": "Blower Motor Control (V2) - Open Circuit",
    "00899": "Blower Motor (V2) - Short to Ground",
    "00600": "Fresh Air Blower (V2) - Final Stage Fault",
    "01325": "Supply Voltage - Too Low",
    "01326": "Supply Voltage - Too High",
    
    # === Control Module ===
    "01330": "Climate Control Module - Internal Fault",
    "00668": "Supply Voltage Terminal 30 - Voltage Too Low",
    "65535": "Internal Control Module Memory Error",
}

ELABORATION_FLAGS = {
    0x00: "No Further Info",
    0x01: "Upper Limit Exceeded",
    0x02: "Lower Limit Exceeded",
    0x04: "No Signal",
    0x08: "Implausible Signal",
    0x10: "Currently Active",
    0x20: "Not Currently Active",
    0x40: "Intermittent",
    0x80: "Not Tested / No Signal",
}

def decode_dtc(code_hi: int, code_lo: int, elaboration: int) -> dict:
    code_val = (code_hi << 8) | code_lo
    code_str = f"{code_val:05d}"
    
    desc = HVAC_DTC_DATABASE.get(code_str, f"Unknown Code {code_str} (Hex: {code_hi:02X} {code_lo:02X})")
    
    status_str = []
    # Simple check for active/intermittent based on elaboration flags
    is_active = False
    is_intermittent = False
    is_stored = True

    if elaboration & 0x10:
        is_active = True
        status_str.append("Currently Active")
    if elaboration & 0x40:
        is_intermittent = True
        status_str.append("Intermittent")
    
    if elaboration == 0x00:
        status_str.append("No Further Info")
    
    for mask, meaning in ELABORATION_FLAGS.items():
        if mask != 0x00 and mask != 0x10 and mask != 0x40 and (elaboration & mask):
            status_str.append(meaning)
            
    status = "Stored"
    if is_active:
        status = "Active"
    elif is_intermittent:
        status = "Intermittent"

    return {
        "code": code_str,
        "description": desc,
        "status": status,
        "details": ", ".join(status_str) if status_str else "Unknown Elaboration",
        "elaboration_hex": f"0x{elaboration:02X}"
    }
