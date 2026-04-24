import serial
import serial.tools.list_ports
import threading
import logging
import time

class SerialError(Exception):
    """Base exception for serial communication errors."""
    pass

class ConnectionError(SerialError):
    """Raised when connection fails."""
    pass

class TimeoutError(SerialError):
    """Raised when a read operation times out."""
    pass

class SerialTransport:
    def __init__(self, port='COM3', baudrate=9600, bytesize=serial.EIGHTBITS, 
                 parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, 
                 timeout=1.0, terminator='\r'):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.terminator = terminator
        
        self.ser = None
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def list_available_ports():
        return [port.device for port in serial.tools.list_ports.comports()]

    def connect(self):
        with self.lock:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()
                
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=self.bytesize,
                    parity=self.parity,
                    stopbits=self.stopbits,
                    timeout=self.timeout
                )
                self.logger.info(f"Connected to {self.port} (Baud: {self.baudrate})")
            except Exception as e:
                self.logger.error(f"Failed to connect to {self.port}: {e}")
                raise ConnectionError(f"Could not open port {self.port}: {e}")

    def disconnect(self):
        with self.lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.logger.info(f"Disconnected from {self.port}.")

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def transaction(self, command, read_until_pattern=None):
        """
        Atomically write a command and read the response.
        If read_until_pattern is provided, it reads until that pattern is found.
        If read_until_pattern is a string, it does an exact match.
        If read_until_pattern has a .search method, it's treated as a regex.
        Otherwise it reads until the default terminator.
        """
        with self.lock:
            if not self.is_connected():
                raise ConnectionError("Serial port is not connected.")
            
            # Clear buffers to ensure a clean transaction
            self.ser.reset_input_buffer()
            
            full_command = (command + self.terminator).encode('ascii')
            self.logger.debug(f"TX: {repr(full_command)}")
            
            start_time = time.time()
            self.ser.write(full_command)
            
            response = b""
            if read_until_pattern:
                if hasattr(read_until_pattern, 'search'):
                    # Regex mode
                    while True:
                        chunk = self.ser.read(self.ser.in_waiting or 1)
                        if not chunk:
                            if (time.time() - start_time) > self.timeout:
                                break
                            continue
                        response += chunk
                        try:
                            decoded = response.decode('ascii', errors='ignore')
                            if read_until_pattern.search(decoded):
                                break
                        except Exception:
                            pass
                else:
                    # String pattern mode
                    pattern_bytes = read_until_pattern.encode('ascii')
                    while True:
                        chunk = self.ser.read_until(pattern_bytes[-1:])
                        if not chunk:
                            if (time.time() - start_time) > self.timeout:
                                break
                            continue
                        response += chunk
                        if response.endswith(pattern_bytes):
                            break
            else:
                response = self.ser.read_until(self.terminator.encode('ascii'))
            
            duration = (time.time() - start_time) * 1000.0
            self.logger.debug(f"RX ({duration:.1f}ms): {repr(response)}")
            return response.decode('ascii')

    def flush(self):
        with self.lock:
            if self.is_connected():
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
