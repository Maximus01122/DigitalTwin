import os
import glob
import time
from fastapi import FastAPI
from pydantic import BaseModel
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

app = FastAPI()

# Configuration
SENSOR_AMBIENT = "28-25c40087f9ef"
SENSOR_MOTOR = "28-651c0087078f"

# L298N Pins
ENA, IN1, IN2 = 18, 17, 27

# Global state
pwm = None
motor_is_killed = True # Default to safe OFF state

if GPIO is not None:
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([ENA, IN1, IN2], GPIO.OUT)
        # Force OFF initially
        GPIO.output(ENA, GPIO.LOW)
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)
        pwm = GPIO.PWM(ENA, 100)
    except Exception as e:
        print(f"Warning: Could not initialize RPi.GPIO: {e}")

def read_temp_raw(sensor_id):
    base_dir = '/sys/bus/w1/devices/'
    device_file = os.path.join(base_dir, sensor_id, 'w1_slave')
    if not os.path.exists(device_file):
        return None
    with open(device_file, 'r') as f:
        lines = f.readlines()
    return lines

def read_temp(sensor_id):
    lines = read_temp_raw(sensor_id)
    if lines is None:
        return None
    # Wait for valid reading
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.1)
        lines = read_temp_raw(sensor_id)
        if lines is None:
            return None
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c
    return None

class KillRequest(BaseModel):
    activate: bool

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/temperature")
def get_temperature():
    global motor_is_killed
    temp_ambient = read_temp(SENSOR_AMBIENT)
    temp_motor = read_temp(SENSOR_MOTOR)
    return {
        "ambient": temp_ambient,
        "motor_surface": temp_motor,
        "timestamp": time.time(),
        "kill_switch_active": motor_is_killed
    }

@app.post("/kill")
def toggle_kill_switch(req: KillRequest):
    global motor_is_killed, pwm
    
    if GPIO is None:
        return {"error": "RPi.GPIO not initialized."}
        
    if req.activate:
        # EMERGENCY KILL: Force everything OFF
        motor_is_killed = True
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)
        if pwm: pwm.ChangeDutyCycle(0)
        return {"kill_switch": "activated", "motor": "OFF"}
    else:
        # POWER ON: Engage Forward at 100% Duty Cycle
        motor_is_killed = False
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
        if pwm: 
            pwm.start(100) # Start/Resume PWM at 100%
        return {"kill_switch": "deactivated", "motor": "ON"}
