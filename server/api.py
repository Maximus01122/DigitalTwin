import asyncio
from fastapi import FastAPI
from pydantic import BaseModel

from hardware import DataCollectingFE, ActuationFE
from middleware import DataPreprocessingFE
from digital_twin import SimulationFE, AnalyticServiceFE, RuleEngine

app = FastAPI()

# Global State
state = {
    "t_physical": 22.0,
    "t_virtual": 22.0,
    "t_ambient": 22.0,
    "residual": 0.0,
    "health_index": 100.0,
    "ttf_minutes": 5.0,
    "motor_enabled": True,
    "kill_triggered": False
}

sensor = DataCollectingFE()
actuator = ActuationFE(pin=17)
filter_fe = DataPreprocessingFE(alpha=0.3)
sim = SimulationFE()
analytics = AnalyticServiceFE()
rules = RuleEngine()

async def control_loop():
    while True:
        # P_heat can be set statically or extracted if we know the voltage/current.
        P_heat = 20.0 if actuator.motor_enabled else 0.0 
        
        # 1. Read Physical Sensor
        raw_act, raw_amb = sensor.read_temperatures()
        t_phys = filter_fe.process(raw_act)
        
        # 2. Digital Twin Simulation
        # Initially assume nominal r_th if analytics hasn't run yet
        current_r_th = analytics.nominal_r_th
        if "current_r_th" in state:
            current_r_th = state["current_r_th"]
            
        t_virt = sim.step(raw_amb, P_heat, r_th_current=current_r_th)
        
        # 3. Analytic Service
        residual, health, dynamic_r_th = analytics.analyze(t_phys, t_virt)
        
        # 4. Rule Engine execution
        ttf, killed = rules.evaluate(t_phys, health, actuator)
        
        # Update State payload
        state["t_physical"] = t_phys
        state["t_virtual"] = t_virt
        state["t_ambient"] = raw_amb
        state["residual"] = residual
        state["health_index"] = health
        state["current_r_th"] = dynamic_r_th
        state["ttf_minutes"] = ttf
        state["motor_enabled"] = actuator.motor_enabled
        state["kill_triggered"] = killed
        
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(control_loop())

@app.get("/state")
def get_state():
    return state

@app.post("/mock/coolant_failure")
def trigger_coolant_failure():
    # Accelerates the mock actual temperature artificially
    if sensor.mock_mode:
        sensor.t_actual += 10.0
    return {"status": "failure injected"}
    
@app.post("/mock/reset")
def reset():
    global state, sim, analytics, rules, actuator, sensor, filter_fe
    sensor = DataCollectingFE()
    actuator = ActuationFE(pin=17)
    filter_fe = DataPreprocessingFE(alpha=0.3)
    sim = SimulationFE()
    analytics = AnalyticServiceFE()
    rules = RuleEngine()
    state["kill_triggered"] = False
    return {"status": "reset"}
