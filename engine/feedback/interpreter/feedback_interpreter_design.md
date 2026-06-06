
# Feedback Interpreter Design (Aligned Full Version)

## Pipeline
Signals → Derived Signals → Rule Mapping → Reason Codes

## Key Dimensions
- layer
- decision_type
- cause_type
- signal_type

## Rule Example
- execution failure → EXEC_FAILURE
- fallback detected → SELECTOR_FALLBACK_USED
- localization fallback → LOCALE_FALLBACK_USED
- personalization fallback → PERS_FALLBACK_LEGACY

## Output
{
  "reason_codes": [],
  "primary_reason": "",
  "confidence": float
}
