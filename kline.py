# kline.py
import serial
import time
import struct
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("KLine")

class KLineException(Exception):
    pass

class KLineTransport:
    def __init__(self, port: str):
        self.port_name = port
        self.ser = None
        self.BAUD_RATE = 4800
        self.INTER_BYTE_DELAY = 0.002 # 2ms

    def _open_serial(self, baudrate=9600):
        if self.ser and self.ser.is_open:
            self.ser.close()
        try:
            self.ser = serial.Serial(
                port=self.port_name,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2.0
            )
            # Ensure lines are idle high
            self.ser.rts = False
            self.ser.dtr = False
            self.ser.break_condition = False
        except Exception as e:
            raise KLineException(f"Failed to open port {self.port_name}: {e}")

    def _precise_sleep(self, duration: float):
        """Busy-wait for precise timing, as time.sleep() can be too inaccurate for bit-banging."""
        end_time = time.perf_counter() + duration
        while time.perf_counter() < end_time:
            pass

    def _set_lines_low(self, is_low: bool):
        """Sets K and L lines low (dominant) or high (recessive)."""
        self.ser.break_condition = is_low
        self.ser.rts = is_low
        self.ser.dtr = is_low

    def slow_init(self, address: int = 0x08) -> bool:
        """Performs the 5-baud initialization sequence on K and L lines."""
        logger.info(f"Starting slow init for address 0x{address:02X} at {self.BAUD_RATE} baud")
        
        # We need to bit-bang the 5 baud signal
        # Each bit is 200ms
        
        self._open_serial(baudrate=self.BAUD_RATE)
        
        # Idle high
        self._set_lines_low(False)
        time.sleep(1.0)
        
        logger.debug("Bit-banging address...")
        
        # Start bit (low)
        self._set_lines_low(True)
        self._precise_sleep(0.2)
        
        # 8 data bits (LSB first)
        for i in range(8):
            bit = (address >> i) & 1
            if bit == 0:
                self._set_lines_low(True)
            else:
                self._set_lines_low(False)
            self._precise_sleep(0.2)
            
        # Stop bit (high)
        self._set_lines_low(False)
        self._precise_sleep(0.2)
        
        logger.debug("Address sent. Waiting for sync byte...")
        
        # Clear out any garbage/echo bytes that arrived in our RX buffer while we were bit-banging TX
        self.ser.reset_input_buffer()
        
        # Now wait for response at normal baud rate
        # ECU should respond with 0x55 (Sync), then two keyword bytes (0x01, 0x8A)
        
        self.ser.timeout = 0.5
        sync_byte = None
        
        # Read up to 10 times to clear any lingering line noise and find the 0x55
        for _ in range(10):
            b = self.ser.read(1)
            if not b:
                continue
            if b[0] == 0x55:
                sync_byte = b
                break
            else:
                logger.debug(f"Ignoring unexpected byte before sync: {b.hex()}")
        
        if not sync_byte:
            raise KLineException("No response to 5-baud init (timeout).")
                
        logger.debug("Received sync byte 0x55")
        
        kw1 = self.ser.read(1)
        kw2 = self.ser.read(1)
        
        if len(kw1) == 0 or len(kw2) == 0:
             raise KLineException("Failed to read keyword bytes.")
             
        logger.debug(f"Received keywords: 0x{kw1[0]:02X}, 0x{kw2[0]:02X}")
        
        # Send complement of kw2
        kw2_comp = (~kw2[0]) & 0xFF
        logger.debug(f"Sending complement of KW2: 0x{kw2_comp:02X}")
        
        # Give ECU a little time
        time.sleep(0.025)
        self.ser.write(bytes([kw2_comp]))
        
        # Read our own echo from the K-Line
        echo = self.ser.read(1)
        if not echo or echo[0] != kw2_comp:
            logger.warning("Did not receive correct echo for KW2 complement.")
        
        # Read back ECU's complement of the address
        addr_comp = self.ser.read(1)
        
        expected_addr_comp = (~address) & 0xFF
        
        if not addr_comp:
            # Some ECUs might not send this, but we'll log it
            logger.warning("Did not receive address complement from ECU.")
        elif addr_comp[0] != expected_addr_comp:
            logger.warning(f"Expected address comp 0x{expected_addr_comp:02X}, got 0x{addr_comp[0]:02X}")
            
        logger.info("Init sequence complete.")
        return True

    def read_byte(self, complement: bool = True) -> int:
        """Reads a byte and optionally sends its complement back."""
        b = self.ser.read(1)
        if not b:
            raise KLineException("Timeout reading byte from K-Line.")
            
        val = b[0]
        if complement:
            comp = (~val) & 0xFF
            time.sleep(self.INTER_BYTE_DELAY)
            self.ser.write(bytes([comp]))
            # Consume our own echo
            echo = self.ser.read(1)
            if not echo or echo[0] != comp:
                raise KLineException(f"Echo mismatch in read_byte. Sent {comp:02X}, got {echo[0] if echo else 'None'}")
            
        return val

    def write_byte(self, val: int, verify_complement: bool = True):
        """Writes a byte and optionally reads back ECU's complement."""
        time.sleep(self.INTER_BYTE_DELAY)
        self.ser.write(bytes([val]))
        
        # Consume our own echo from the K-Line
        echo = self.ser.read(1)
        if not echo or echo[0] != val:
            raise KLineException(f"Echo mismatch in write_byte. Sent {val:02X}, got {echo[0] if echo else 'None'}")
        
        if verify_complement:
            b = self.ser.read(1)
            if not b:
                raise KLineException(f"Timeout waiting for complement of 0x{val:02X}")
            comp = b[0]
            expected = (~val) & 0xFF
            if comp != expected:
                 logger.warning(f"Byte write complement mismatch. Sent 0x{val:02X}, expected 0x{expected:02X}, got 0x{comp:02X}")

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
