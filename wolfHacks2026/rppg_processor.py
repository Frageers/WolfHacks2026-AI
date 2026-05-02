import numpy as np

def calculate_biometric_severity(reported_pain, heart_rate, signal_confidence):
    """
    reported_pain: 0-10 (from questionnaire)
    heart_rate: BPM (from rPPG)
    signal_confidence: 0.0-1.0 (based on lighting/motion)
    """
    
    # 1. Calculate 'Expected' HR based on reported pain
    # Normal resting HR ~70. Pain usually increases HR.
    # If HR is 110 but pain is 3, there's a 'Discrepancy'
    
    hr_severity_map = {
        (0, 85): 2.0,   # Normal
        (86, 100): 5.0,  # Elevated (Moderate pain/Stress)
        (101, 125): 8.0, # High (Acute pain/Distress)
        (126, 200): 10.0 # Extreme (Shock/Cardiac event)
    }
    
    # Find base biometric severity
    bio_severity = 2.0
    for (low, high), val in hr_severity_map.items():
        if low <= heart_rate <= high:
            bio_severity = val
            break

    # 2. Robust Blending
    # If confidence is low (poor lighting), we trust the user more.
    # If confidence is high, we trust the heart rate more.
    
    calibrated_severity = (signal_confidence * bio_severity) + ((1 - signal_confidence) * reported_pain)
    
    # Safety Check: If bio_severity is high (HR 120), never go below 7.0 
    # even if user says pain is 1 and lighting is 'okay'.
    if bio_severity >= 8.0 and signal_confidence > 0.4:
        return max(calibrated_severity, 8.0)
        
    return round(calibrated_severity, 1)