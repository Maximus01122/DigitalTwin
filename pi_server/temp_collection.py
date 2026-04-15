import time
import csv
import RPi.GPIO as GPIO

# --- UNIFIED CONFIGURATION ---
SENSOR_AMBIENT = "28-08d2008770d0"
SENSOR_MOTOR = "28-651c0087078f"

# Pin Setup (L298N)
ENA, IN1, IN2 = 18, 17, 27


DURATION = 9000       # 3 hours in seconds

# --- INITIALIZATION ---
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup([ENA, IN1, IN2], GPIO.OUT)
pwm = GPIO.PWM(ENA, 1000)

file_name = "run.csv"

def read_temp(sensor_id):
    """Reads temperature from 1-Wire DS18B20 sensor."""
    try:
        path = f"/sys/bus/w1/devices/{sensor_id}/w1_slave"
        with open(path, "r") as f:
            lines = f.readlines()
            temp_line = lines[1].find("t=")
            if temp_line != -1:
                return float(lines[1][temp_line+2:]) / 1000.0
    except Exception:
        return None

print(f"🚀 Calibration started. Target Duration: {DURATION/3600:.1f} hours.")

try:
    # Start Motor
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    pwm.start(100)
    
    start_time = time.time()
    
    # Open both CSV files simultaneously
    with open(file_name, "w", newline='') as f:
        writer = csv.writer(f)
        
        # Write Headers
        writer.writerow(["seconds", "t_motor", "t_ambient"])
        
        while True:
            elapsed = round(time.time() - start_time, 2)
            
            # Read sensors ONCE per loop to keep data perfectly synced
            t_m = read_temp(SENSOR_MOTOR)
            t_a = read_temp(SENSOR_AMBIENT)
            
            if t_m is not None and t_a is not None:
                writer_a.writerow([elapsed, t_m, t_a])
                fa.flush()
                
                # Console output for monitoring
                print(f"Time: {int(elapsed)}s | Motor: {t_m}°C | Amb: {t_a}°C")
            
            # Check for completion
            if elapsed > DURATION:
                print(f"Test Complete: {DURATION/3600:.1f} hours reached.")
                break
                
except KeyboardInterrupt:
    print("\nCalibration interrupted by user.")
finally:
    pwm.stop()
    GPIO.cleanup()
    print("Motor stopped. System cleaned up.")
