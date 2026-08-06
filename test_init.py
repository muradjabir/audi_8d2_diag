import serial
import time
import sys

def precise_sleep(duration):
    end = time.perf_counter() + duration
    while time.perf_counter() < end:
        pass

def try_init(port, baudrate):
    print(f"\n--- Trying {baudrate} baud ---")
    try:
        ser = serial.Serial(port, baudrate=baudrate, timeout=0.5)
        ser.rts = False
        ser.dtr = False
        ser.break_condition = False
        time.sleep(1.0)
        
        # Bit-bang 0x08 at 5 baud
        address = 0x08
        
        # Start bit
        ser.break_condition = True
        ser.rts = True
        ser.dtr = True
        precise_sleep(0.2)
        
        for i in range(8):
            bit = (address >> i) & 1
            low = (bit == 0)
            ser.break_condition = low
            ser.rts = low
            ser.dtr = low
            precise_sleep(0.2)
            
        # Stop bit
        ser.break_condition = False
        ser.rts = False
        ser.dtr = False
        precise_sleep(0.2)
        
        ser.reset_input_buffer()
        
        print("Waiting for response...")
        response = ser.read(10)
        print(f"Received ({len(response)} bytes): {response.hex()}")
        
        ser.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import serial.tools.list_ports
    ports = [p.device for p in serial.tools.list_ports.comports() if 'usbserial' in p.device.lower() or 'ftdi' in p.description.lower()]
    if not ports:
        print("No FTDI ports found.")
        sys.exit(1)
    port = ports[0]
    print(f"Using port: {port}")
    
    try_init(port, 9600)
    time.sleep(2)
    try_init(port, 10400)
    time.sleep(2)
    try_init(port, 4800)
