from flask import Flask, render_template, request, jsonify
from scrape import scrape_er_watch, parse_to_sites
from gnn_engine import get_gnn_recommendation # Assuming your GNN logic is here

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/triage', methods=['POST'])
def triage():
    data = request.json or {}

    # Extract Manual inputs
    age      = int(data.get('age', 30))
    pain     = int(data.get('pain', 0))
    pain_loc = data.get('pain_loc', [])
    cardiac  = data.get('cardiac', [])
    neuro    = data.get('neuro', [])
    
    # 1. Base Severity Calculation
    severity = float(max(
        int(data.get('speak', 1)), 
        int(data.get('walk', 1)), 
        int(data.get('breath', 1)), 
        int(data.get('focus', 1))
    ))

    # Pain/Cardiac escalation
    if pain >= 7 or 'chest_pain' in cardiac or 'chest' in pain_loc:
        severity = max(severity, 8.5)
    elif pain >= 4:
        severity = max(severity, 5.0)

    # 2. rPPG Biometric Fixer (The "Stoic Patient" Logic)
    rppg_hr   = float(data.get('rppg_hr', 0))
    rppg_conf = float(data.get('rppg_confidence', 0.0))
    
    rppg_applied = False
    if rppg_hr > 40 and rppg_conf > 0.4:
        # Clinical HR Thresholds for Acute Distress
        if rppg_hr > 120:   bio_score = 9.5
        elif rppg_hr > 105: bio_score = 8.0
        elif rppg_hr > 90:  bio_score = 6.0
        else: bio_score = severity

        # Confidence-weighted blend
        # If lighting is good (0.9), bio_score dominates.
        calibrated = (rppg_conf * bio_score) + ((1 - rppg_conf) * severity)
        
        if calibrated > severity:
            severity = calibrated
            rppg_applied = True

    severity = round(min(severity, 10.0), 1)

    # 3. Get Real-Time Hospital Data
    raw_hospitals = scrape_er_watch()
    sites = parse_to_sites(raw_hospitals)

    # 4. GNN Routing
    u_lat = data.get('lat', 43.73)
    u_lon = data.get('lon', -79.74)
    
    if not sites:
        return jsonify({"error": "No hospital data available"}), 503

    best_site, logs = get_gnn_recommendation(severity, u_lat, u_lon, sites)

    return jsonify({
        "target":        best_site['name'],
        "wait":          best_site['wait'],
        "calc_severity": severity,
        "sites_used":    len(sites),
        "rppg_active":   rppg_applied,
        "debug_log":     logs
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)