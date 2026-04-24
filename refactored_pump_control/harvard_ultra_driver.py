import logging
import re
from .pump_driver_base import PumpDriverBase

class HarvardUltraDriver(PumpDriverBase):
    """
    Driver for Harvard Apparatus PHD Ultra / Pump 11 Elite using 'Pump Chain' protocol.
    Sync-centric: queries the pump for current settings.
    """
    
    PROMPT_MAP = {
        ':': 'stopped',
        '>': 'infusing',
        '<': 'withdrawing',
        '*': 'stalled',
        'T*': 'target volume reached'
    }

    def __init__(self, transport, address=0):
        self.transport = transport
        self.address = address # 0-99
        self.logger = logging.getLogger(__name__)
        self.last_status_code = None
        self.prompt_regex = re.compile(rf"{self._format_address()}([:><\*]|T\*)")

    def _format_address(self):
        return f"{self.address:02d}"

    def _send_command(self, command, args="", read_mode="cr"):
        full_command = f"{self._format_address()}{command}"
        if args:
            full_command += f" {args}"
        
        pattern = None
        if read_mode == "prompt":
            pattern = self.prompt_regex
            
        response = self.transport.transaction(full_command, read_until_pattern=pattern)
        self._parse_status(response)
        return response

    def _parse_status(self, response):
        match = self.prompt_regex.findall(response)
        if match:
            # findall returns groups if defined in regex, but we want the code
            # Let's use search or findall carefully
            # match is a list of captured groups, e.g. [':']
            self.last_status_code = match[-1]

    def verify_connection(self):
        try:
            resp = self._send_command("ver", read_mode="cr")
            return "Ultra" in resp or "Elite" in resp or self.last_status_code is not None
        except Exception:
            return False

    def get_syringe_info(self):
        """
        Syncs syringe manufacturer, model, and diameter from the pump.
        Uses 'syrm' and 'syrd' commands.
        """
        try:
            # Get manufacturer and model string
            syrm_resp = self._send_command("syrm", read_mode="cr")
            # Example: 00:BD plastic, 5 ml, 11.989 mm\r\n00:
            clean_syrm = re.sub(rf"{self._format_address()}[:><\*]", "", syrm_resp).strip()
            
            # Try to get diameter from syrm response first (often included in newer firmware)
            dia_match = re.search(r'([\d\.]+)\s*mm', clean_syrm)
            if dia_match:
                diameter = float(dia_match.group(1))
            else:
                # Fallback to syrd
                syrd_resp = self._send_command("syrd", read_mode="cr")
                dia_match = re.search(r'([\d\.]+)', syrd_resp)
                diameter = float(dia_match.group(1)) if dia_match else 0.0
            
            # Simple parsing for Manufacturer/Model
            parts = clean_syrm.split(',', 2)
            manufacturer = parts[0].strip() if len(parts) > 0 else "Unknown"
            model = parts[1].strip() if len(parts) > 1 else "Unknown"
            
            return {
                'manufacturer': manufacturer,
                'model': model,
                'diameter_mm': diameter
            }
        except Exception as e:
            self.logger.error(f"Failed to sync syringe info: {e}")
            raise

    def set_rate(self, rate, units="ul/h", direction="infuse"):
        # Map units to pump-friendly format (e.g. ul/h -> ul/hr)
        p_units = units.replace("/h", "/hr").replace("/m", "/min")
        cmd = "irat" if direction == "infuse" else "wrat"
        return self._send_command(cmd, f"{rate} {p_units}", read_mode="prompt")

    def get_rate(self):
        resp = self._send_command("irat", read_mode="cr")
        # Example: 00:1.5000 ml/hr\n00:
        # Regex to handle flexible units and multiple prompts
        match = re.search(r'[:><\*]\s*([\d\.]+)\s*([\w\/]+)', resp)
        if match:
            return float(match.group(1)), match.group(2)
        return None, None

    def run(self, direction=None):
        if direction == "infuse":
            return self._send_command("irun", read_mode="prompt")
        elif direction == "withdraw":
            return self._send_command("wrun", read_mode="prompt")
        else:
            return self._send_command("run", read_mode="prompt")

    def stop(self):
        return self._send_command("stp", read_mode="prompt")

    def get_status(self):
        self._send_command("", read_mode="prompt")
        return self.PROMPT_MAP.get(self.last_status_code, 'unknown')
