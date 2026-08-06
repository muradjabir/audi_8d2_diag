# kwp1281.py
import time
import logging
from kline import KLineTransport, KLineException

logger = logging.getLogger("KWP1281")

class KWP1281Exception(Exception):
    pass

class KWP1281:
    def __init__(self, port: str):
        self.transport = KLineTransport(port)
        self.block_counter = 0
        self.connected = False
        
    def connect(self, address: int = 0x08) -> dict:
        """Connect to ECU and read identification."""
        try:
            self.transport.slow_init(address)
            self.connected = True
            
            # The ECU will now send identification blocks.
            # We read them until we get a block that doesn't say "more info follows"
            
            ecu_info = {
                "part_number": "",
                "coding": "",
                "workshop_code": "",
                "extra": []
            }
            
            # Usually ECUs send 0xF6 (ASCII string) blocks
            while True:
                length, counter, title, data = self.receive_block()
                if title == 0xF6:
                    text = "".join(chr(c) for c in data if 32 <= c <= 126)
                    if not ecu_info["part_number"]:
                        ecu_info["part_number"] = text
                    else:
                        ecu_info["extra"].append(text)
                
                # Check if this is the last block of the connection sequence
                if title == 0x09: # ACK, shouldn't really happen here but just in case
                    break
                    
                # To get next block, we must send an ACK (0x09)
                self.send_ack()
                
                # In real KWP1281, 0x03 as title means end of communication, but we are just looking for the end of the ID phase.
                # Actually, some ECUs just send all info, then wait for command. 
                # A common pattern is: ECU sends 0xF6 (info), Tester sends 0x09 (ACK), ECU sends next 0xF6, Tester sends 0x09...
                # Finally ECU sends 0x09 to say "I'm ready for commands". Let's assume we break when ECU sends 0x09.
                if title == 0x09:
                    break
                    
            return ecu_info
            
        except KLineException as e:
            self.connected = False
            self.transport.close()
            raise KWP1281Exception(f"Connection failed: {e}")

    def disconnect(self):
        """End communication gracefully."""
        if self.connected:
            try:
                self.send_block(0x06, []) # 0x06 is often End Communication
            except Exception:
                pass
            self.connected = False
        self.transport.close()

    def receive_block(self):
        """Receives a KWP1281 block."""
        try:
            length = self.transport.read_byte()
            if length == 0:
                raise KWP1281Exception("Received block length 0")
                
            counter = self.transport.read_byte()
            self.block_counter = (counter + 1) % 256
            
            title = self.transport.read_byte()
            
            data = []
            for _ in range(length - 3):
                data.append(self.transport.read_byte())
                
            end_byte = self.transport.read_byte(complement=False) # 0x03 has no complement
            
            if end_byte != 0x03:
                logger.warning(f"Block did not end with 0x03, got 0x{end_byte:02X}")
                
            logger.debug(f"Received block: len={length}, ctr={counter}, title=0x{title:02X}, data={[hex(d) for d in data]}")
            return length, counter, title, data
            
        except KLineException as e:
            self.connected = False
            raise KWP1281Exception(f"Failed to receive block: {e}")

    def send_block(self, title: int, data: list):
        """Sends a KWP1281 block."""
        length = len(data) + 3
        
        logger.debug(f"Sending block: len={length}, ctr={self.block_counter}, title=0x{title:02X}, data={[hex(d) for d in data]}")
        
        try:
            self.transport.write_byte(length)
            self.transport.write_byte(self.block_counter)
            self.transport.write_byte(title)
            
            for d in data:
                self.transport.write_byte(d)
                
            self.transport.write_byte(0x03, verify_complement=False) # End byte has no complement
            
            self.block_counter = (self.block_counter + 1) % 256
            
        except KLineException as e:
            self.connected = False
            raise KWP1281Exception(f"Failed to send block: {e}")

    def send_ack(self):
        """Sends an ACK block."""
        self.send_block(0x09, [])

    def read_dtcs(self) -> list:
        """Reads Diagnostic Trouble Codes."""
        if not self.connected:
            raise KWP1281Exception("Not connected")
            
        self.send_block(0x07, [])
        
        dtcs_raw = []
        
        while True:
            length, counter, title, data = self.receive_block()
            
            if title == 0x09:
                break
                
            if title == 0xFC: # DTC response
                # Data comes in triplets usually: Code_High, Code_Low, Elaboration/Status
                for i in range(0, len(data), 3):
                    if i + 2 < len(data):
                        hi = data[i]
                        lo = data[i+1]
                        elab = data[i+2]
                        if hi == 0xFF and lo == 0xFF:
                            # 0xFFFF means end of faults
                            pass
                        else:
                            dtcs_raw.append({"hi": hi, "lo": lo, "elaboration": elab})
            
            self.send_ack()
                
        return dtcs_raw

    def clear_dtcs(self):
        """Clears stored DTCs."""
        if not self.connected:
            raise KWP1281Exception("Not connected")
            
        self.send_block(0x05, [])
        while True:
            length, counter, title, data = self.receive_block()
            if title == 0x09:
                break
            self.send_ack()
        
    def read_meas_block(self, group: int) -> list:
        """Reads a specific measurement group."""
        if not self.connected:
            raise KWP1281Exception("Not connected")
            
        self.send_block(0x29, [group])
        
        raw_measurements = []
        while True:
            length, counter, title, data = self.receive_block()
            
            if title == 0x09:
                break
                
            if title == 0xE7:
                # Data comes in triplets: Formula, A, B
                for i in range(0, len(data), 3):
                    if i + 2 < len(data):
                        raw_measurements.append({
                            "formula": data[i],
                            "a": data[i+1],
                            "b": data[i+2]
                        })
            
            self.send_ack()
            
        return raw_measurements
