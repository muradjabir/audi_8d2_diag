# port_scanner.py
import serial.tools.list_ports

def scan_ports() -> list[dict]:
    """Returns list of candidate KKL ports."""
    ports = serial.tools.list_ports.comports()
    candidates = []
    
    for port in ports:
        # Prioritize FTDI and common USB-to-Serial
        is_likely = False
        desc = port.description.lower()
        hwid = port.hwid.lower()
        
        if "ftdi" in desc or "ftdi" in hwid or "0403" in hwid:
            is_likely = True
        elif "usb" in desc or "ch340" in desc or "serial" in desc:
            is_likely = True
            
        candidates.append({
            "device": port.device,
            "description": port.description,
            "is_likely": is_likely
        })
        
    # Sort likely ports first
    candidates.sort(key=lambda x: not x["is_likely"])
    return candidates

def auto_select() -> str | None:
    """Returns the best-guess port, or None if ambiguous or none found."""
    ports = scan_ports()
    if not ports:
        return None
        
    likely_ports = [p for p in ports if p["is_likely"]]
    
    if len(likely_ports) == 1:
        return likely_ports[0]["device"]
    elif len(likely_ports) > 1:
        # If multiple likely, return None to force user choice
        return None
    elif len(ports) > 0:
        # Fallback to first available if no obvious candidate
        return ports[0]["device"]
        
    return None
