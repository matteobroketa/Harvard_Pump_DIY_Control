from abc import ABC, abstractmethod

class PumpDriverBase(ABC):
    @abstractmethod
    def verify_connection(self):
        """Strictly verifies that the pump is connected and responsive."""
        pass

    @abstractmethod
    def get_syringe_info(self):
        """
        Queries the pump for the active syringe configuration.
        Returns a dict: {'manufacturer': str, 'model': str, 'diameter_mm': float}
        """
        pass

    @abstractmethod
    def set_rate(self, rate, units="ul/h", direction="infuse"):
        """Sets the flow rate."""
        pass

    @abstractmethod
    def get_rate(self):
        """Gets the current flow rate and units."""
        pass

    @abstractmethod
    def run(self, direction=None):
        """Starts the pump."""
        pass

    @abstractmethod
    def stop(self):
        """Stops the pump."""
        pass

    @abstractmethod
    def get_status(self):
        """Gets the pump status (stopped, infusing, withdrawing, stalled)."""
        pass
