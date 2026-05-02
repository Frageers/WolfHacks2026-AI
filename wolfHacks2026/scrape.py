import requests
import json
import re

CLASSIFICATION_CAPABILITY = {
    'A': 10,  # Major trauma / quaternary
    'B': 8,   # Full community ER
    'C': 5,   # Small rural hospital
    'D': 9,   # Regional specialty
    'E': 7,   # Extended services
    'G': 5,   # General inpatient
    'M': 4,   # Medicine / non-emergency
    'N': 4,   # Nursing
    'V': 3,   # Urgent care only — cannot handle CTAS 1/2
    'K': 3,
    'J': 3,
}

# Hard overrides for known misclassified sites
CAPABILITY_OVERRIDES = {
    "OHC17": 4,   # Peel Memorial — urgent care, NOT a trauma ER
    "OHC2":  3,   # Prospect Blvd — day surgery only
}

def classification_to_capability(hospital_id, classification_str):
    if hospital_id in CAPABILITY_OVERRIDES:
        return CAPABILITY_OVERRIDES[hospital_id]
    if not classification_str:
        return 6
    codes  = [c.strip() for c in classification_str.split(',')]
    scores = [CLASSIFICATION_CAPABILITY.get(c, 0) for c in codes]
    return max(scores) if scores else 6

def format_wait(minutes):
    if minutes < 60:
        return f"{minutes} min"
    hours = minutes // 60
    mins  = minutes % 60
    return f"{hours}h {mins}m" if mins else f"{hours}h"

def scrape_er_watch():
    url = "https://www.er-watch.ca"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TriageBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    matches = re.findall(r'self\.__next_f\.push\(\[1,"(.+?)"\]\)', resp.text, re.DOTALL)

    for chunk in matches:
        try:
            decoded = chunk.encode().decode('unicode_escape')
        except Exception:
            decoded = chunk

        if '"estimated_wait_time"' in decoded and '"coordinates"' in decoded:
            match = re.search(r'"hospitals":\[(.+?)\],"sponsors"', decoded, re.DOTALL)
            if match:
                try:
                    return json.loads('[' + match.group(1) + ']')
                except json.JSONDecodeError:
                    continue
    return []

def parse_to_sites(hospitals):
    sites = []
    for h in hospitals:
        if not h.get('hasLiveData'):
            continue
        wait_minutes = h.get('estimated_wait_time')
        if wait_minutes is None:
            continue
        coords = h.get('coordinates', {})
        lat = coords.get('lat', 0)
        lon = coords.get('lng', 0)
        if lat == 0 or lon == 0:
            continue

        capability = classification_to_capability(h['id'], h.get('classification', ''))

        sites.append({
            "id":         h['id'],
            "name":       h['name'],
            "city":       h.get('city', ''),
            "type":       "ER",
            "wait_val":   wait_minutes,
            "wait":       format_wait(wait_minutes),
            "capability": capability,
            "lat":        lat,
            "lon":        lon,
        })
    return sites