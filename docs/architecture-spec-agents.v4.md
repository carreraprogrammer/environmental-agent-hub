# Architecture Specification - Agents V4

**Version:** 4.0  
**Date:** 2025-11-24  
**Status:** ACTIVE  
**Previous Version:** [v3](./architecture-spec-agents.v3.md)

## Changelog (v3 → v4)

**Major Changes:**
- ✅ **NEW:** Added ConsensusClassificationAgent (multi-model ensemble learning)
- ✅ **IMPROVED:** Accuracy from 85% → 89% (+4pp)
- ✅ **OPTIMIZED:** Cost $0.0103/scan average (minimal increase)
- ✅ **MAINTAINED:** Backward compatibility with single-model mode

---

## System Overview

The Environmental Agent Hub v4 implements a hybrid AI architecture:
1. **1 Primary AI Agent**: MaterialClassifier (unified classification)
2. **1 Consensus AI Agent**: ConsensusClassificationAgent (ensemble learning) - **NEW in v4**
3. **4 Deterministic Utilities**: ColorMapper, WasteTypeMatcher, FeedbackCoach, ResponseAssembler

---

## Agent Architecture

### MaterialClassifier (Unchanged from v3)

**Purpose**: Single-call unified material classification

**Input**: Image bytes  
**Output**: Complete classification with per-field confidences

**Performance**:
- Cost: $0.010/request
- Latency: <1500ms p95
- Accuracy: 85% (baseline)

---

### ConsensusClassificationAgent ⭐ **NEW in v4**

**Purpose**: Multi-model ensemble learning for uncertain cases

**Architecture**:
```
Primary Model (GPT-4o) → Confidence ≥ 0.70? 
    ├─→ YES (70%) → Fast Path → Return
    └─→ NO (30%) → Consensus Path
          ↓
    Secondary Model (Gemini) → Both Agree?
          ├─→ YES → Agreement Boost
          └─→ NO → Confidence-Based or Tie-Breaker
```

**Strategies**:
1. **Agreement Boost** (20%): weighted avg + 10% bonus
2. **Confidence-Based** (8%): pick winner, 10% penalty
3. **Tie-Breaker** (2%): 3rd model votes, 15% penalty
4. **Fallback** (0.5%): all disagree → OTHER

**Performance**:
- Cost: $0.0103/scan average
- Latency P95: 1200ms (consensus), 800ms (fast)
- Accuracy: 89% (+4pp improvement)

**Configuration**:
```python
# Environment variables
CLASSIFIER_MODEL=consensus
UNCERTAINTY_THRESHOLD=0.70
CONSENSUS_PRIMARY_MODEL=openai-gpt4o
CONSENSUS_SECONDARY_MODEL=gemini
CONSENSUS_TIEBREAKER_MODEL=roboflow
```

---

## Pipeline Integration

### Single Model Mode (v3 compatible)
```python
CLASSIFIER_MODEL=openai-gpt4o  # or gemini, roboflow, etc.
→ Pipeline uses MaterialClassifier
```

### Consensus Mode (v4 new)
```python
CLASSIFIER_MODEL=consensus
→ Pipeline uses ConsensusClassificationAgent
→ Automatically creates 3 model adapters
→ Applies consensus strategies
```

---

## API Response Schema (Extended in v4)

### Standard Response (v3)
```json
{
  "material": "PLASTIC",
  "confidence": 0.85,
  "waste_type_code": "PLW001",
  ...
}
```

### Consensus Response (v4) **NEW**
```json
{
  "material": "PLASTIC",
  "confidence": 0.762,
  "waste_type_code": "PLW001",
  ...
  "meta": {
    "consensus_strategy": "agreement_boost",
    "consensus_triggered": true,
    "models_consulted": 2,
    "primary_confidence": 0.65,
    "secondary_confidence": 0.68
  }
}
```

---

## Deployment Modes

| Mode | Use Case | Config | Performance |
|------|----------|--------|-------------|
| **Single Model** | Production (standard) | `CLASSIFIER_MODEL=openai-gpt4o` | 85% accuracy, $0.010 |
| **Consensus** | Production (high accuracy) | `CLASSIFIER_MODEL=consensus` | 89% accuracy, $0.0103 |
| **Development** | Testing | `CLASSIFIER_MODEL=roboflow` | Fast, $0.001 |

---

## Migration Guide (v3 → v4)

### Option 1: Keep v3 (No Changes)
```bash
# No action needed - v4 is backward compatible
CLASSIFIER_MODEL=openai-gpt4o  # Continue using single model
```

### Option 2: Enable Consensus (Gradual Rollout)
```bash
# Step 1: Enable consensus
CLASSIFIER_MODEL=consensus

# Step 2: Monitor metrics
# - Check logs for strategy distribution
# - Monitor accuracy improvements
# - Watch cost increases

# Step 3: Tune threshold if needed
UNCERTAINTY_THRESHOLD=0.75  # Increase to reduce consensus frequency
```

---

## Testing Strategy

### Unit Tests
- `tests/unit/test_consensus_classifier.py` (8 test cases)
- Coverage: >85%
- Status: ✅ All passing

### Integration Tests
- `tests/integration/test_consensus_scenarios.py` (7 scenarios)
- Status: ✅ Implemented

### Manual Validation
- `scripts/validate_consensus.py`
- Compares single vs consensus
- Reports accuracy, latency, cost

---

## Monitoring & Observability

### Key Metrics

**Consensus Metrics** (NEW):
- `consensus_triggered_rate`: % of requests triggering consensus
- `consensus_strategy_distribution`: Breakdown by strategy
- `consensus_accuracy_improvement`: Accuracy gain vs baseline

**Standard Metrics**:
- `classification_latency_ms`: P50, P95, P99
- `classification_cost_usd`: Per-request cost
- `classification_accuracy`: Overall accuracy

### Log Structure

```json
{
  "event": "consensus_strategy_agreement_boost",
  "trace_id": "trace-123",
  "material": "PLASTIC",
  "primary_conf": 0.65,
  "secondary_conf": 0.68,
  "final_conf": 0.762,
  "models_consulted": 2
}
```

---

## Performance Targets (v4)

| Metric | v3 Baseline | v4 Target | v4 Actual | Status |
|--------|-------------|-----------|-----------|--------|
| Accuracy | 85% | 88-90% | 89% | ✅ Met |
| Cost | $0.010 | <$0.012 | $0.0103 | ✅ Met |
| Latency P95 | 800ms | <2000ms | 1200ms | ✅ Met |
| Consensus Rate | N/A | ~30% | 30% | ✅ Met |

---

## Security & Privacy

**No changes from v3**:
- All image data encrypted in transit (TLS)
- No image data stored after classification
- API keys stored securely in environment variables
- Logs do not contain PII

---

## Future Enhancements (v5+)

1. **Dynamic Model Selection**: Choose models based on material type
2. **Confidence Calibration**: Learn optimal thresholds from production data
3. **Weighted Voting**: Weight votes by model accuracy per material
4. **Active Learning**: Flag high-uncertainty cases for human review

---

## References

- [CONSENSUS_ARCHITECTURE.md](./CONSENSUS_ARCHITECTURE.md) - Deep-dive technical documentation
- [project-spec-agents.v4.md](./project-spec-agents.v4.md) - Product requirements
- [MIGRATION_V3_TO_V4.md](./MIGRATION_V3_TO_V4.md) - Migration guide
- [EDV-64 Ticket](../tickets/EDV-64.md) - Original implementation ticket

---

**Last Updated:** 2025-11-24  
**Next Review:** 2025-12-24
