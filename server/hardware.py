import time
import random

# Attempt to import real Raspberry Pi libraries, fallback to mocking on Mac/Windows
MOCK_MODE = False
try:
    from w1thermsensor import W1ThermSensor
    import RPi.GPIO as GPIO
except ImportError:
    MOCK_MODE = True
    print("WARNING: Hardware modules not found. Running in MOCK_MODE.")

class DataCollectingFE:
    """Reads actual and ambient temperature via 1-Wire or mocked logic."""
    def __init__(self):
        self.mock_mode = MOCK_MODE
        
        if self.mock_mode:
            self.t_ambient = 22.0
            self.t_actual = 22.0
            self.heating = True
        else:
            self.sensors = W1ThermSensor.get_available_sensors()

    def read_temperatures(self):
        """Returns (T_actual, T_ambient)"""
        if self.mock_mode:
            # Mock thermal drift scenario
            if self.heating:
                self.t_actual += (75.0 - self.t_actual) * 0.05 + random.uniform(-0.5, 0.5)
            else:
                self.t_actual += (self.t_ambient - self.t_actual) * 0.05 + random.uniform(-0.5, 0.5)
                
            return self.t_actual, self.t_ambient
        else:
            # Physical read 
            # Assuming sensor 0 is actual, sensor 1 is ambient
            if len(self.sensors) >= 2:
                t_act = self.sensors[0].get_temperature()
                t_amb = self.sensors[1].get_temperature()
            elif len(self.sensors) == 1:
                t_act = self.sensors[0].get_temperature()
                t_amb = 22.0 # Fallback
            else:
                t_act, t_amb = 25.0, 25.0
            return t_act, t_amb

class ActuationFE:
    """Controls the L298N driver Kill Switch via GPIO."""
    def __init__(self, pin=17):
        self.mock_mode = MOCK_MODE
        self.pin = pin
        self.motor_enabled = True
        
        if not self.mock_mode:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            GPIO.output(self.pin, GPIO.HIGH) # HIGH = ON
            
    def kill_motor(self):
        self.motor_enabled = False
        if self.mock_mode:
            print("[MOCK] KILL SWITCH ACTIVATED! Motor disabled.")
        else:
            GPIO.output(self.pin, GPIO.LOW) # LOW = OFF
            
    def enable_motor(self):
        self.motor_enabled = True
        if self.mock_mode:
            print("[MOCK] Motor ENABLED.")
        else:
            GPIO.output(self.pin, GPIO.HIGH)
