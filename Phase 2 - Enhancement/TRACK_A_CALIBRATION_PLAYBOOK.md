# TRACK_A_CALIBRATION_PLAYBOOK.md

Phase 2 Track A: Scoring & Severity Calibration

This playbook describes how to improve the Phase 1 scoring system without breaking contracts.

---

## A. Current Phase 1 Behavior

In `(5.1) severity_detector.py`, element scores are derived from severity bin midpoints:
- `severity_to_score(severity)` finds the severity's bin in `SCORE_TO_SEVERITY` and returns `(lo+hi)/2`.
- `section_coverage` is computed per element as fraction of sections where any hook severity >= threshold.

This is deterministic and stable, but coarse.

---

## B. Phase 2 Calibration Strategy

We calibrate scores *after* base inference.

### B1. Severity-midpoint override (safe)
- Adjust representative midpoints per severity.
- Does not change severity labels.
- Use when you want better spacing between buckets.

### B2. Feature model (optional)
- Compute a chart-level calibration scalar from SectionMetrics features.
- Blend with severity midpoint to shift global score calibration.
- Keep element ordering stable while correcting global bias.

---

## C. How to Run Calibration

1) Create / edit the config:
- `score_calibration_config_v0.1.0.json`

2) Use the calibrated wrapper:
```python
from proseka_score_calibration import infer_severities_for_chart_calibrated

result = infer_severities_for_chart_calibrated(
    sections,
    calibration_config_path='score_calibration_config_v0.1.0.json',
    preserve_severity=True,
)
```

3) Feed `result['elements_skeleton']` into selection/guidance as usual.

---

## D. Evaluation Checklist

Recommended evaluation metrics:
- Rank correlation against human ordering or QA labels.
- Stability: selection should not oscillate with minor metric noise.
- Bucket sanity: demanding should remain rare; slight should remain common.
- Tips compliance: word limits and tone remain within spec.

---

## E. Integration Points

Preferred integration:
- swap `(5.1) severity_detector.py` import in adapters to call the calibrated wrapper.

Non-breaking method:
- keep Phase 1 code, add a runtime toggle (config path) in production adapters.

END
