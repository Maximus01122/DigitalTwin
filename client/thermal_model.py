import numpy as np
import time

class ThermalDigitalTwin:
    def __init__(self, calibration=None):
        self.mass = 0.165  # kg (31ZY exact weight)
        self.specific_heat = 460 # J/(kg*K) for steel
        self.surface_area = 0.05 # m^2
        
        if calibration is None:
            # Default to the 4-run joint fit calibration (propeller on, 100% PWM)
            calibration = {
                "T_ss_offset": 3.24,
                "tau_seconds": 671,
                "h_effective": 2.263,
                "Q_waste_watts": 0.366
            }
            
        self.h = calibration["h_effective"]
        
        # Base input power for normal mechanical operation (12V * ~150mA = 1.8W)
        self.base_input_power = 1.8
        self.input_power = self.base_input_power
        
        # Derive efficiency mathematically from Q_waste to ensure accurate heat tracking
        self.efficiency = 1.0 - (calibration["Q_waste_watts"] / self.base_input_power)
        
        # History
        self.history_temps = []
        self.history_times = []
        
        # Ghost Motor State
        self.theoretical_surface = None
        
    def update_ghost_motor(self, ambient_temp, dt_seconds):
        if self.theoretical_surface is None:
            self.theoretical_surface = ambient_temp
            
        heat_generated = self.input_power * (1 - self.efficiency)
        heat_dissipated = self.h * self.surface_area * (self.theoretical_surface - ambient_temp)
        thermal_mass = self.mass * self.specific_heat
        
        # Euler step for pure mathematical parallel
        self.theoretical_surface += ((heat_generated - heat_dissipated) / thermal_mass) * dt_seconds
        return self.theoretical_surface

    def get_anomaly_residual(self, actual_surface):
        if self.theoretical_surface is None:
            return 0.0
        return actual_surface - self.theoretical_surface


    def calculate_ttf(self, current_temp, max_safe_temp=35.0):
        """
        Calculates Time-To-Failure (TTF) in seconds based on recent temperature trends.
        """
        if len(self.history_temps) < 10:
            return float('inf') # Need more data for a stable derivative
            
        recent_times = self.history_times[-20:]
        recent_temps = self.history_temps[-20:]
        
        if recent_times[-1] == recent_times[0]:
            return float('inf')
            
        # Linear slope derivation (dT/dt)
        slope = (recent_temps[-1] - recent_temps[0]) / (recent_times[-1] - recent_times[0])
        
        if slope <= 0:
            return float('inf') # Motor is cooling or stable
            
        remaining_temp = max_safe_temp - current_temp
        if remaining_temp <= 0:
            return 0.0 # Already failed/exceeded max temp
            
        ttf_seconds = remaining_temp / slope
        return ttf_seconds
        
    def add_reading(self, timestamp, temperature):
        if len(self.history_times) > 0 and timestamp == self.history_times[-1]:
            return # Avoid duplicates
            
        self.history_times.append(timestamp)
        self.history_temps.append(temperature)
        
        # Prune memory
        if len(self.history_temps) > 100:
            self.history_temps.pop(0)
            self.history_times.pop(0)
