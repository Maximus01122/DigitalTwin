class SimulationFE:
    """
    Implements a first-order Lumped Thermal Model.
    dT/dt = (1 / C_th) * (P_heat - (T_virtual - T_ambient) / R_th)
    """
    def __init__(self, c_th=150.0, r_th=0.5):
        self.c_th = c_th   # Thermal Capacitance (J/K)
        self.r_th = r_th   # Thermal Resistance (K/W), inversely proportional to cooling health (h)
        self.t_virtual = 22.0
        self.dt = 1.0      # System execution period (1Hz in seconds)
        
    def step(self, t_ambient, p_heat, r_th_current=None):
        """Simulates one time step of the motor heating up."""
        if r_th_current is None:
            r_th_current = self.r_th
            
        heat_loss = (self.t_virtual - t_ambient) / r_th_current
        delta_t = (1.0 / self.c_th) * (p_heat - heat_loss) * self.dt
        self.t_virtual += delta_t
        return self.t_virtual

class AnalyticServiceFE:
    """Estimates the cooling health based on the physical vs digital residual."""
    def __init__(self, nominal_r_th=0.5):
        self.nominal_r_th = nominal_r_th
        self.residual = 0.0
        self.health_index = 100.0
        
    def analyze(self, t_physical, t_virtual):
        self.residual = abs(t_physical - t_virtual)
        
        # A simple linear degradation metric: If residual grows over 5C, health approaches 0
        # This is a proxy for the 'h' estimation
        degradation = min((self.residual / 5.0) * 100, 100.0)
        self.health_index = 100.0 - degradation
        
        # Calculate dynamic R_th based on health (if health goes down, resistance goes up)
        # e.g., if cooling fan fails, resistance to heat loss increases
        current_r_th = self.nominal_r_th * (1.0 + (degradation / 50.0)) 
        return self.residual, self.health_index, current_r_th

class RuleEngine:
    """Deterministic logic to trigger Actuation FE."""
    def __init__(self, max_temp_limit=60.0, min_ttf_minutes=5.0):
        self.max_temp_limit = max_temp_limit
        self.min_ttf_minutes = min_ttf_minutes
        
    def evaluate(self, t_physical, health_index, actuation_fe):
        # Calculate naive Time-to-Failure
        # If temp is rising by e.g. 0.5 deg per sec, TTF is (Limit - Temp) / Rate
        # For simplicity, if health index drops below 20%, trigger
        
        trigger_kill = False
        reason = ""
        
        if t_physical >= self.max_temp_limit:
            trigger_kill = True
            reason = f"Temperature Critical ({t_physical:.1f}C > Limit {self.max_temp_limit}C)"
            
        if health_index <= 20.0:
            trigger_kill = True
            reason = f"Cooling Health Critical ({health_index:.1f}% <= 20%)"
            
        # Simplified TTF Metric (minutes) based on remaining temp delta and assuming a linear heat-up worst case
        # (This would be more rigorous dynamically in the analytical FE)
        ttf_min = (self.max_temp_limit - t_physical) / 2.0  # mock worst-case rate
        if ttf_min < 0: ttf_min = 0
        
        if trigger_kill and actuation_fe.motor_enabled:
            actuation_fe.kill_motor()
            print(f"RULE ENGINE TRIGGERED: {reason}")
            
        return ttf_min, trigger_kill
