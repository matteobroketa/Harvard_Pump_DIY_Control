import json

class RampPolicy:
    PRESETS = {
        "stepped_fine":     {"interval_ms": 100,  "min_delta": 0.001, "max_hz": 10.0, "max_divergence": 0.05},
        "stepped_adaptive": {"interval_ms": 500,  "min_delta": 0.01,  "max_hz": 2.0,  "max_divergence": 0.5},
        "stepped_coarse":   {"interval_ms": 2000, "min_delta": 0.1,   "max_hz": 0.5,  "max_divergence": 2.0},
        "custom":           {"interval_ms": 500,  "min_delta": 0.01,  "max_hz": 2.0,  "max_divergence": 0.5}
    }

    def __init__(self, mode="stepped_adaptive"):
        self.mode = mode
        self.apply_preset(mode)

    def apply_preset(self, mode):
        settings = self.PRESETS.get(mode, self.PRESETS["stepped_adaptive"])
        self.interval_ms = settings["interval_ms"]
        self.min_delta = settings["min_delta"]
        self.max_hz = settings["max_hz"]
        self.max_divergence = settings["max_divergence"]
        self.suppress_redundant = True

    def to_dict(self):
        return {
            "mode": self.mode,
            "interval_ms": self.interval_ms,
            "min_delta": self.min_delta,
            "max_hz": self.max_hz,
            "max_divergence": self.max_divergence
        }

    @classmethod
    def from_dict(cls, data):
        mode = data.get("mode", "stepped_adaptive")
        policy = cls(mode=mode)
        # Always override with saved values if they exist
        policy.interval_ms = data.get("interval_ms", policy.interval_ms)
        policy.min_delta = data.get("min_delta", policy.min_delta)
        policy.max_hz = data.get("max_hz", policy.max_hz)
        policy.max_divergence = data.get("max_divergence", policy.max_divergence)
        return policy

class HoldSegment:
    def __init__(self, rate, units, duration_seconds, direction="infuse"):
        self.type = "hold"
        self.rate = float(rate)
        self.units = units
        self.duration = float(duration_seconds)
        self.direction = direction

    def get_ideal_rate(self, t):
        return self.rate

    def to_dict(self):
        return {"type": "hold", "rate": self.rate, "units": self.units, "duration": self.duration, "direction": self.direction}

class RampSegment:
    def __init__(self, start_rate, end_rate, units, duration_seconds, direction="infuse"):
        self.type = "ramp"
        self.start_rate = float(start_rate)
        self.end_rate = float(end_rate)
        self.units = units
        self.duration = float(duration_seconds)
        self.direction = direction

    def get_ideal_rate(self, t):
        if t <= 0: return self.start_rate
        if t >= self.duration: return self.end_rate
        return self.start_rate + (self.end_rate - self.start_rate) * (t / self.duration)

    def to_dict(self):
        return {"type": "ramp", "start_rate": self.start_rate, "end_rate": self.end_rate, "units": self.units, "duration": self.duration, "direction": self.direction}

class PumpProfile:
    def __init__(self, name="New Profile"):
        self.name = name
        self.segments = []
        self.policy = RampPolicy()

    def add_segment(self, segment):
        self.segments.append(segment)

    def total_duration(self):
        return sum(s.duration for s in self.segments)

    def get_ideal_rate_at(self, t):
        accumulated = 0.0
        for seg in self.segments:
            if accumulated <= t < (accumulated + seg.duration):
                return seg.get_ideal_rate(t - accumulated)
            accumulated += seg.duration
        if not self.segments: return 0.0
        return self.segments[-1].get_ideal_rate(self.segments[-1].duration)

    def to_dict(self):
        return {
            "name": self.name,
            "policy": self.policy.to_dict(),
            "segments": [s.to_dict() for s in self.segments]
        }

    @classmethod
    def from_dict(cls, data):
        profile = cls(name=data.get("name", "Loaded Profile"))
        if "policy" in data:
            profile.policy = RampPolicy.from_dict(data["policy"])
        
        for seg_data in data.get("segments", []):
            seg_type = seg_data.get("type")
            if seg_type == "hold":
                profile.add_segment(HoldSegment(
                    rate=seg_data["rate"],
                    units=seg_data["units"],
                    duration_seconds=seg_data["duration"],
                    direction=seg_data.get("direction", "infuse")
                ))
            elif seg_type == "ramp":
                profile.add_segment(RampSegment(
                    start_rate=seg_data["start_rate"],
                    end_rate=seg_data["end_rate"],
                    units=seg_data["units"],
                    duration_seconds=seg_data["duration"],
                    direction=seg_data.get("direction", "infuse")
                ))
            else:
                raise ValueError(f"Unknown segment type: {seg_type}")
        return profile

    def save_to_file(self, path):
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, path):
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
