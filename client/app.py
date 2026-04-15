import streamlit as st
import requests
import pandas as pd
import altair as alt
from thermal_model import ThermalDigitalTwin

# Settings
PI_URL = "http://raspberrypi.local:8000"

MAX_SAFE_TEMP = 35.0

st.set_page_config(
    page_title="Thermal Digital Twin",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    .metric-box {
        background: linear-gradient(145deg, #1e1e1e, #2a2a2a);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.05);
        text-align: center;
        box-shadow: inset 0 2px 4px rgba(255,255,255,0.02), 0 8px 16px rgba(0,0,0,0.4);
        transition: transform 0.2s ease-in-out;
    }
    .metric-box:hover {
        transform: translateY(-2px);
    }
    .metric-title {
        color: #9cb2c7;
        font-size: 1rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }
    .val-normal { color: #f0f0f0; }
    .status-warning { color: #ffca28; }
    .status-ok { color: #00e676; text-shadow: 0 0 10px rgba(0,230,118,0.3); }
    .status-critical { 
        color: #ff1744; 
        text-shadow: 0 0 15px rgba(255,23,68,0.5);
        animation: pulse 1s infinite alternate; 
    }
    @keyframes pulse {
      0% { transform: scale(1); }
      100% { transform: scale(1.05); }
    }
    
    /* Completely disable Streamlit's native 'running' dimming effect */
    [data-stale="true"] {
        opacity: 1 !important;
        filter: none !important;
        transition: none !important;
    }
    [data-testid="stFragment"] {
        opacity: 1 !important;
        transition: none !important;
    }
</style>
""", unsafe_allow_html=True)

# State Management
if 'dt_model' not in st.session_state:
    st.session_state.dt_model = ThermalDigitalTwin(
        {
            "T_ss_offset": 3.24,
            "tau_seconds": 671,
            "h_effective": 2.263,
            "Q_in": 0.366
        })
if 'data_log' not in st.session_state:
    st.session_state.data_log = []

# API Helpers
def fetch_pi_data():
    try:
        req = requests.get(f"{PI_URL}/temperature", timeout=5)
        if req.status_code == 200:
            return req.json()
    except Exception as e:
        return None
    return None

def trigger_kill_switch(activate=True):
    try:
        requests.post(f"{PI_URL}/kill", json={"activate": activate}, timeout=5)
    except:x
    pass

# Dashboard Main UI
st.title("🔥 12V Motor Thermal Digital Twin")
st.markdown("Real-time edge telemetry, predictive lumped capacitance modeling, and automated safety overrides.")

@st.fragment(run_every=0.25)
def complete_dashboard():
    data = fetch_pi_data()

    if data is None:
        st.error("No connection to Raspberry Pi Edge Node API! Retrying...")
        return

    ambient = data.get("ambient")
    surface = data.get("motor_surface")
    timestamp = data.get("timestamp")
    kill_active = data.get("kill_switch_active", False)

    # Fail-safes if hardware is disconnected but server is running
    if ambient is None: ambient = 25.0
    if surface is None: surface = 25.0

    # Digital Twin Model Step
    dt = st.session_state.dt_model
    dt.add_reading(timestamp, surface)
    ttf = dt.calculate_ttf(surface, MAX_SAFE_TEMP)
    
    # Dynamic Time Calculation
    # We cannot assume exactly 2.0 seconds pass. Network lag or fast-forwarding 
    # the dummy server means we must trace the true timestamp delta!
    if 'last_dt_timestamp' not in st.session_state:
        st.session_state.last_dt_timestamp = timestamp
        dt_seconds = 2.0
    else:
        dt_seconds = timestamp - st.session_state.last_dt_timestamp
        st.session_state.last_dt_timestamp = timestamp
        
    if dt_seconds <= 0.0:
        dt_seconds = 2.0 # Failsafe
    
    # Ghost Motor anomaly detection
    # Cut heat generation input to 0 if the motor is mechanically OFF
    dt.input_power = dt.base_input_power if not kill_active else 0.0
    ghost_temp = dt.update_ghost_motor(ambient, dt_seconds)
    print("new", timestamp, dt_seconds)
    residual = dt.get_anomaly_residual(surface)

    # Log it
    st.session_state.data_log.append({
        "time": pd.to_datetime(timestamp, unit='s'),
        "surface_temp": surface,
        "ambient_temp": ambient,
        "ghost_temp": ghost_temp
    })

    if len(st.session_state.data_log) > 10000:
        st.session_state.data_log = st.session_state.data_log[-10000:]

    # Predictive Auto-Kill & Anomaly Alerts
    critical_temp = surface >= MAX_SAFE_TEMP
    critical_ttf = ttf < 300 # 5 mins
    critical_anomaly = residual >= 3.0

    if (critical_temp or critical_ttf) and not kill_active:
        trigger_kill_switch(True)
        st.toast("🔥 PREDICTIVE FAILURE IMMINENT! Kill Switch Auto-Engaged.", icon="🚨")
        
    if critical_anomaly:
        st.error(f"🚨 ANOMALY DETECTED: Motor is pulling +{residual:.1f}°C unexplained excess heat! (Physical resistance, short, or stall likely).")

    # Top Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"<div class='metric-box'><div class='metric-title'>Ambient Temp</div><div class='metric-value val-normal'>{ambient:.1f}°C</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-box'><div class='metric-title'>Surface Temp</div><div class='metric-value val-normal'>{surface:.1f}°C</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-box'><div class='metric-title'>Ghost Twin</div><div class='metric-value val-normal'>{ghost_temp:.1f}°C</div></div>", unsafe_allow_html=True)
    with col4:
        anomaly_cls = "status-critical" if critical_anomaly else "status-ok"
        st.markdown(f"<div class='metric-box'><div class='metric-title'>Residual</div><div class='metric-value {anomaly_cls}'>+{max(0, residual):.1f}°C</div></div>", unsafe_allow_html=True)
    with col5:
        ttf_str = f"{ttf:.0f}s" if ttf != float('inf') else "Stable"
        status_cls = "status-critical" if ttf < 300 else "status-warning" if ttf < 600 else "status-ok"
        if ttf == float('inf'): status_cls = "val-normal"
        st.markdown(f"<div class='metric-box'><div class='metric-title'>Predictive TTF</div><div class='metric-value {status_cls}'>{ttf_str}</div></div>", unsafe_allow_html=True)

    st.divider()

    # Chart
    chart_data = pd.DataFrame(st.session_state.data_log)
    if not chart_data.empty:
        chart_data_melted = chart_data.melt(id_vars=['time'], value_vars=['surface_temp', 'ambient_temp', 'ghost_temp'],
                                           var_name='Measurement', value_name='Temperature (°C)')
        
        # Prettier Names
        measure_map = {'surface_temp': 'Motor Surface', 'ambient_temp': 'Ambient Environment', 'ghost_temp': 'Ghost Motor (Expected)'}
        chart_data_melted['Measurement'] = chart_data_melted['Measurement'].map(measure_map)

        c = alt.Chart(chart_data_melted).mark_line(strokeWidth=3, interpolate='basis').encode(
            x=alt.X('time:T', title='Time'),
            y=alt.Y('Temperature (°C):Q', scale=alt.Scale(domain=[min(20.0, ambient), MAX_SAFE_TEMP])),
            color=alt.Color('Measurement:N', scale=alt.Scale(domain=['Ambient Environment', 'Ghost Motor (Expected)', 'Motor Surface'], range=['#9cb2c7', '#00e676', '#ffca28'])),
            tooltip=['time', 'Temperature (°C)', 'Measurement']
        ).properties(height=450).interactive()
        
        st.altair_chart(c, use_container_width=True)

    st.subheader("Manual Controls & Safety Overrides")
    k1, k2, k3 = st.columns([1,1,2])
    
    if k1.button("🟢 POWER MOTOR ON", use_container_width=True):
        trigger_kill_switch(False) # Turn off kill switch to allow power
        st.rerun()
        
    if k2.button("🚨 ENGAGE EMERGENCY KILL", use_container_width=True, type="primary"):
        trigger_kill_switch(True) # Engage kill switch to cut power
        st.rerun()
        
    if kill_active:
        st.error("🛑 MAIN POWER SEVERED: MOTOR IS OFF")
    else:
        st.success("⚡ POWER ENGAGED: MOTOR IS LIVE")

# Run the live fragment
complete_dashboard()
