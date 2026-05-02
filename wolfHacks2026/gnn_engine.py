import math

def get_gnn_recommendation(severity, user_lat, user_lon, current_sites):
    best_node = None
    min_score = float('inf')
    debug_log = []

    # Hard filter: severity 8+ must go to a full ER (capability >= 8)
    if severity >= 8.0:
        eligible = [s for s in current_sites if s['capability'] >= 8]
        if not eligible:
            eligible = current_sites
        debug_log.append(f"[Filter] severity={severity} → {len(eligible)} ER-only sites")

    # Mid severity: clinics can't handle it, needs urgent care or ER
    elif severity >= 4.0:
        eligible = [s for s in current_sites if s['capability'] >= 4]
        if not eligible:
            eligible = current_sites
        debug_log.append(f"[Filter] severity={severity} → {len(eligible)} urgent care+ sites")

    # Low severity: everything is eligible, clinics will win on wait time
    else:
        eligible = current_sites
        debug_log.append(f"[Filter] severity={severity} → all {len(eligible)} sites eligible")

    for site in eligible:
        dist_km = math.sqrt(
            (site['lat'] - user_lat)**2 + (site['lon'] - user_lon)**2
        ) * 111

        # Wait penalty — decreases as severity rises
        wait_penalty = site['wait_val'] * (1 - (severity / 10))

        # Distance penalty — scales with severity
        dist_penalty = dist_km * (1 + severity)

        # Under-capability penalty — site can't handle patient
        gap = severity - site['capability']
        if gap > 0:
            safety_penalty = gap * 15
        else:
            safety_penalty = 0

        # Over-qualification penalty — don't send mild cases to trauma ERs
        # A severity 1 patient at a capability 8 ER wastes a bed
        over_qual = site['capability'] - severity
        if over_qual > 4:
            overqual_penalty = over_qual * 8
        else:
            overqual_penalty = 0

        total_score = wait_penalty + dist_penalty + safety_penalty + overqual_penalty

        debug_log.append(
            f"{site['name']}: {round(total_score,1)} "
            f"(wait={round(wait_penalty,1)} dist={round(dist_penalty,1)} "
            f"safety={round(safety_penalty,1)} overqual={round(overqual_penalty,1)} "
            f"cap={site['capability']})"
        )

        if total_score < min_score:
            min_score = total_score
            best_node = site

    return best_node, debug_log