import logging
from .serial_transport import SerialTransport

class TransportManager:
    _instance = None
    _transports = {} # port_name -> SerialTransport

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TransportManager, cls).__new__(cls)
        return cls._instance

    def get_transport(self, port, baudrate=9600):
        if port not in self._transports:
            logging.info(f"Creating new transport for {port}")
            self._transports[port] = SerialTransport(port=port, baudrate=baudrate)
        return self._transports[port]

    def release_transport(self, port):
        # We might want to keep it alive if others are using it, 
        # but for now, simple cleanup if it exists.
        if port in self._transports:
            self._transports[port].disconnect()
            # Note: In a true daisy-chain, we'd count references 
            # before actually deleting.
            # del self._transports[port]
