import csv
import numpy as np
from scipy.optimize import curve_fit
import json

times = []
temps = []
with open('/Users/maximilianfuchs/.gemini/antigravity/scratch/thermal_dt/run_off.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            times.append(float(row['seconds']))
            temps.append(float(row['t_motor']))
        except ValueError:
            pass

t = np.array(times)
T = np.array(temps)

# The dataset starts at T_amb=23.5 and actually the first reading T_actual is 23.3
T_start = T[0]

# Heating curve: T(t) = T_start + T_ss * (1 - e^(-t / tau))
def heating_curve(t, T_ss, tau):
    return T_start + T_ss * (1 - np.exp(-t / tau))

popt, _ = curve_fit(heating_curve, t, T, p0=[20, 1000])
T_ss, tau = popt

mass = 0.165 # kg
c = 460 # J/kg*K (steel approx)

# tau = mc / (h A) => h*A = mc / tau
surface_area = 0.05
h = (mass * c / tau) / surface_area

# T_ss = Qin / (h A) => Qin = T_ss * h * A
Qin = T_ss * h * surface_area

print(json.dumps({
    "T_ss_offset": T_ss,
    "tau_seconds": tau,
    "h_effective": h,
    "Q_waste_watts": Qin
}, indent=2))
