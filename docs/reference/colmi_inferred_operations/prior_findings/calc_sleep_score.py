#!/usr/bin/env python3
"""
QRing Sleep Score Calculator
inferred from com.qcwireless.smart.ui.home.sleep.aigo.AlSleepUtil

Port of the Java calcSleepScore() and calScore() methods.
Validated against APK-derived reference material v1.0.1.108.

O (Obsidian), March 30 2026
"""

import sqlite3
import sys
from pathlib import Path


def cal_score(actual: float, target: float, max_weight: float) -> float:
    """
    Score one component: how close is actual to target?
    Returns max_weight * (1 - |actual - target| / target)
    Clamped to [0, max_weight]. Can theoretically go negative if actual > 2*target.
    """
    deviation = abs(actual - target)
    return max_weight * (1.0 - deviation / target)


def calc_sleep_score(total_sec: int, deep_sec: int, light_sec: int, awake_times: int = 0) -> int:
    """
    Calculate QRing sleep score (0-100).
    
    Args:
        total_sec: Total sleep duration in seconds
        deep_sec: Deep sleep duration in seconds
        light_sec: Light sleep duration in seconds
        awake_times: Number of awake events (always 0 in QRing app)
    
    Returns:
        Sleep score 0-100
    """
    # Target values for each component
    targets = [0.2, 0.5, 100.0, 250.0, 500.0]
    
    # Weight distribution (sums to 100 when awake_times=0)
    # [0] deep ratio:      2.5 pts
    # [1] light ratio:     2.5 pts  
    # [2] deep minutes:    5.0 pts
    # [3] light minutes:   5.0 pts
    # [4] total minutes:  70.0 pts  <-- DOMINANT
    # [5] awake penalty:  15.0 pts  (free points, never actually penalized)
    weights = [2.5, 2.5, 5.0, 5.0, 70.0, 15.0]
    
    total_min = total_sec / 60.0
    deep_min = deep_sec / 60.0
    light_min = light_sec / 60.0
    
    if total_min <= 0:
        return 0
    
    # Values to score against targets
    actuals = [
        deep_min / total_min,    # deep ratio (target: 0.2 = 20%)
        light_min / total_min,   # light ratio (target: 0.5 = 50%)
        deep_min,                # deep absolute (target: 100 min)
        light_min,               # light absolute (target: 250 min)
        total_min,               # total duration (target: 500 min = 8h20m)
    ]
    
    subtotal = 0.0
    for i in range(5):
        score = cal_score(actuals[i], targets[i], weights[i])
        subtotal += max(0.0, score)
    
    # Awake penalty: 15 pts minus 3.75 per wakeup (but always 0 wakeups in practice)
    awake_bonus = weights[5] - (weights[5] / 4.0) * awake_times
    awake_bonus = max(0.0, awake_bonus)
    
    return round(subtotal + awake_bonus)


def score_label(score: int) -> str:
    """Map score to QRing label."""
    if score < 60:
        return "Poor"
    elif score < 75:
        return "Fair"
    elif score < 90:
        return "Good"
    else:
        return "Excellent"


def efficiency_display(score: int) -> str:
    """Map score to QRing's cosmetic 'efficiency' display."""
    if score < 60:
        return "80%"
    elif score < 70:
        return "82%"
    elif score < 80:
        return "85%"
    elif score < 85:
        return "90%"
    elif score < 90:
        return "95%"
    elif score < 95:
        return "99%"
    else:
        return "100%"


def main():
    db_path = Path("/tmp/ring_data_copy.sqlite")
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(db_path))
    
    import json
    from datetime import datetime, timedelta
    
    # Get the latest capture that has segments and a parsed summary
    row = conn.execute("""
        SELECT src.sleep_capture_id, src.requested_at, src.parsed_summary_json
        FROM sleep_raw_captures src
        WHERE src.sleep_capture_id = (SELECT MAX(sleep_capture_id) FROM sleep_segments)
    """).fetchone()
    
    if not row:
        print("No sleep data found.")
        sys.exit(1)
    
    capture_id, requested_at, summary_json = row
    summary = json.loads(summary_json) if summary_json else None
    
    if not summary or 'days' not in summary:
        print("No parsed day structure in latest capture.")
        sys.exit(1)
    
    # The segments table has per-day segments. offset_minutes resets to 0 at day boundaries.
    # Use the 'days' from parsed summary to know how many segments per day.
    segments = conn.execute("""
        SELECT sequence_no, sleep_type, duration_minutes, offset_minutes
        FROM sleep_segments
        WHERE sleep_capture_id = ?
        ORDER BY sequence_no
    """, (capture_id,)).fetchall()
    
    # Group segments by day using the period_count from parsed summary
    capture_date = datetime.fromisoformat(requested_at.replace('+00:00', '+00:00'))
    days = summary['days']
    
    seg_idx = 0
    print(f"{'Night (ago)':<14} {'Bed->Wake':<16} {'Total':>6} {'Deep':>5} {'Light':>6} {'REM':>5} {'Awake':>6} {'Score':>5} {'Label':<10}")
    print("-" * 88)
    
    for day_info in days:
        days_ago = day_info['days_ago']
        period_count = day_info['period_count']
        sleep_start = day_info.get('sleep_start_time', '??:??')
        sleep_end = day_info.get('sleep_end_time', '??:??')
        
        # Collect this day's segments
        deep_min = 0
        light_min = 0
        rem_min = 0
        awake_min = 0
        nodata_min = 0
        
        for i in range(period_count):
            if seg_idx < len(segments):
                _, stype, dur, _ = segments[seg_idx]
                if stype == 'deep':
                    deep_min += dur
                elif stype == 'light':
                    light_min += dur
                elif stype == 'rem':
                    rem_min += dur
                elif stype == 'awake':
                    awake_min += dur
                elif stype == 'nodata':
                    nodata_min += dur
                seg_idx += 1
        
        # Total sleep = deep + light + REM (awake is monitored time, not sleep)
        # But QRing's totalSleep in SleepViewBean includes everything the ring reported
        # The scoring function uses totalSleep which appears to be deep+light+REM+awake
        total_sleep_min = deep_min + light_min + rem_min + awake_min
        total_h = total_sleep_min / 60
        
        if total_sleep_min <= 0:
            continue
        
        # Score it (convert minutes to seconds)
        score = calc_sleep_score(
            total_sec=total_sleep_min * 60,
            deep_sec=deep_min * 60,
            light_sec=light_min * 60,
            awake_times=0
        )
        
        night_date = (capture_date - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        label = score_label(score)
        
        print(f"{night_date} ({days_ago}d) {sleep_start}->{sleep_end:>5} {total_h:5.1f}h {deep_min:4d}m {light_min:5d}m {rem_min:4d}m {awake_min:5d}m {score:>5} {label:<10}")
    
    conn.close()
    
    # Show a few example calculations
    print("\n--- Example calculations ---")
    examples = [
        ("Perfect 8h20m sleep", 500*60, 100*60, 250*60, 0),
        ("Short 5h sleep", 300*60, 60*60, 150*60, 0),
        ("Long 10h sleep", 600*60, 120*60, 300*60, 0),
        ("All deep (unrealistic)", 500*60, 500*60, 0, 0),
        ("All light (unrealistic)", 500*60, 0, 500*60, 0),
        ("With 2 wakeups", 500*60, 100*60, 250*60, 2),
        ("With 4+ wakeups", 500*60, 100*60, 250*60, 4),
    ]
    
    for name, total, deep, light, awake in examples:
        score = calc_sleep_score(total, deep, light, awake)
        print(f"  {name:<30} -> Score: {score:>3} ({score_label(score)})")


if __name__ == "__main__":
    main()
