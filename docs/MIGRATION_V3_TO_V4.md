# Migration Guide: V3 → V4

## Overview

This guide helps you migrate from Agent Hub V3 to V4. The V4 architecture introduces significant improvements in performance, cost, and simplicity through agent fusion and edge computing.

## Summary of Changes

### Key Architectural Changes

| Component | V3 | V4 | Impact |
|-----------|----|----|--------|
| **PreValidator** | GPT-4o-mini for anti-troll | Roboflow Object Detection + Technical validations | Breaking change |
| **Classification** | 3 separate agents (Classifier, SubtypeDetector, VolumeEstimator) | 1 unified MaterialClassifier | Breaking change |
| **Adapters** | `classify(image_url)` only | `classify_material(image_bytes)` added | New method |
| **Schemas** | Simple `ClassificationResult` | Complex `MaterialClassificationResult` with per-field confidences | New schemas |
| **Cost** | $0.031/request | $0.011/request | 65% reduction |
| **Latency** | 3-5s | 0.8-1.2s | 70% improvement |
| **Agents** | 10 backend agents | 5-6 backend agents | Simpler pipeline |

---

## Breaking Changes

### 1. PreValidator Schema Change

**V3 Schema:**
```python
class ValidationResult:
    has_waste: bool
    confidence: float
    reason: str
```

**V4 Schema:**
```python
class ValidationResult:
    is_valid: bool
    reason: ValidationReason  # Enum instead of string
    metadata: dict  # New: Roboflow detections data
    cost: float = 0.001  # New: API cost tracking
    fallback_used: bool = False  # New: Fallback indicator
```

**Migration:**
```python
# V3
if result.has_waste:
    proceed_to_classification()

# V4
if result.is_valid:
    proceed_to_classification()
```

### 2. Classifier → MaterialClassifier

**V3: Three separate agents**
```python
# Classifier
classifier_result = await classifier.classify(image_url)
# → material: WasteMaterial, confidence: float

# SubtypeDetector
subtype_result = await subtype_detector.detect(image_url, material)
# → subtype: str

# VolumeEstimator
volume_result = await volume_estimator.estimate(image_url)
# → volume_liters: float
```

**V4: One unified agent**
```python
# MaterialClassifier
classification = await material_classifier.classify(image_bytes, trace_id)
# → MaterialClassificationResult with:
#   - material: MaterialField
#   - subtype: SubtypeField
#   - condition: ConditionField
#   - volume: VolumeField
#   - recyclability: RecyclabilityField
#   - reasoning: str
#   - timestamp: datetime
#   - cost: float
#   - partial_success: bool
```

**Migration:**
```python
# V3
material = classifier_result.material
subtype = subtype_result.subtype
volume = volume_result.volume_liters

# V4
material = classification.material.material_type
subtype = classification.subtype.value  # Can be None if low confidence
volume = classification.volume.liters  # Can be None if low confidence

# Handle partial success
if classification.partial_success:
    logger.warning(f"Partial success: some fields have low confidence")
```

### 3. Adapter Method Addition

**V3: Only `classify()` method**
```python
class ClassifierAdapter(ABC):
    @abstractmethod
    async def classify(self, image_url: str) -> ClassificationResult:
        pass
```

**V4: Added `classify_material()` method**
```python
class ClassifierAdapter(ABC):
    @abstractmethod
    async def classify(self, image_url: str) -> ClassificationResult:
        """V3 compatibility - DEPRECATED"""
        pass

    @abstractmethod
    async def classify_material(self, image_data: bytes) -> dict[str, Any]:
        """V4 unified classification"""
        pass
```

**Migration:**
```python
# V3
result = await adapter.classify(image_url)

# V4 (recommended)
result_dict = await adapter.classify_material(image_bytes)

# V3 compatibility (deprecated, still works)
result = await adapter.classify(image_url)
```

---

## Step-by-Step Migration

### Step 1: Update Dependencies

```bash
# Update requirements.txt
pip install anthropic>=0.8.0  # New: Claude Sonnet 4.5 support
pip install pillow>=10.0.0  # For image processing

# Verify
python -c "import anthropic; print(anthropic.__version__)"
```

### Step 2: Update PreValidator Usage

```python
# V3
validator = PreValidator()
result = await validator.validate(image_bytes, trace_id)
if result.has_waste:
    # Continue

# V4
validator = PreValidator(
    model_id="workspace/waste-hsysm/6",  # Roboflow model
    confidence_threshold=0.4,
    overlap_threshold=0.5,
)
result = await validator.validate(image_bytes, trace_id)
if result.is_valid:
    # Continue

# Access new metadata
if not result.fallback_used:
    detected_classes = result.metadata.get("classes", [])
    num_detections = result.metadata.get("num_detections", 0)
```

### Step 3: Replace Classifier with MaterialClassifier

```python
# V3
classifier = ClassifierFactory.create("openai")
result = await classifier.classify(image_url)

# V4
from app.agents.material_classifier import MaterialClassifier
from app.adapters.openai_adapter import OpenAIClassifierAdapter

adapter = OpenAIClassifierAdapter(model="gpt-4o")
classifier = MaterialClassifier(adapter)

classification = await classifier.classify(image_bytes, trace_id)

# Access all fields
print(f"Material: {classification.material.material_type}")
print(f"Confidence: {classification.material.confidence}")
print(f"Subtype: {classification.subtype.value}")
print(f"Volume: {classification.volume.liters}L")
print(f"Recyclability: {classification.recyclability.value}")
print(f"Reasoning: {classification.reasoning}")

# Handle partial success
if classification.partial_success:
    if classification.subtype.value is None:
        logger.warning("Subtype confidence too low, using generic material")
    if classification.volume.liters is None:
        logger.warning("Volume confidence too low, proceeding without volume")
```

### Step 4: Update Environment Variables

```bash
# Add to .env
ROBOFLOW_API_KEY=your_roboflow_api_key
ROBOFLOW_MODEL_ID=workspace/waste-hsysm/6
ANTHROPIC_API_KEY=your_anthropic_api_key  # Optional, for Claude support
```

### Step 5: Update Tests

```python
# V3 Test
async def test_classifier():
    classifier = OpenAIClassifierAdapter()
    result = await classifier.classify("https://example.com/image.jpg")
    assert result.material == WasteMaterial.PLASTIC

# V4 Test
async def test_material_classifier():
    adapter = OpenAIClassifierAdapter(model="gpt-4o")
    classifier = MaterialClassifier(adapter)

    with open("tests/fixtures/pet_bottle.jpg", "rb") as f:
        image_bytes = f.read()

    result = await classifier.classify(image_bytes, "test-trace-id")

    # Test all fields
    assert result.material.material_type == Material.PLASTIC
    assert result.material.confidence >= 0.7
    assert result.subtype.value == "PET"
    assert result.subtype.recycling_code == "#1"
    assert result.volume.liters is not None
    assert not result.partial_success
```

---

## Configuration Changes

### V3 Config
```python
# config/models.yaml
classifier:
  provider: openai
  model: gpt-4o
  timeout: 30
```

### V4 Config
```python
# config/models.yaml
prevalidator:
  provider: roboflow
  model_id: workspace/waste-hsysm/6
  confidence_threshold: 0.4
  overlap_threshold: 0.5
  timeout: 3
  fallback_on_error: true

material_classifier:
  provider: openai  # or anthropic, google
  model: gpt-4o  # or claude-3-5-sonnet-20241022, gemini-1.5-pro-vision
  timeout: 30
  min_material_confidence: 0.7
  min_subtype_confidence: 0.6
  min_volume_confidence: 0.5
```

---

## Common Migration Issues

### Issue 1: Missing Roboflow API Key

**Error:**
```
ValueError: ROBOFLOW_API_KEY not found in environment
```

**Solution:**
```bash
# Add to .env
ROBOFLOW_API_KEY=your_key_here
ROBOFLOW_MODEL_ID=workspace/waste-hsysm/6
```

### Issue 2: Partial Success Handling

**Problem:** V4 returns `null` for some fields (subtype, volume)

**Solution:**
```python
# Handle partial success explicitly
if classification.subtype.value is None:
    # Use generic material classification
    material_only = classification.material.material_type
else:
    # Use specific subtype
    full_classification = f"{classification.material.material_type}-{classification.subtype.value}"

if classification.volume.liters is None:
    # Proceed without volume data
    logger.info("Volume not available, using default")
```

### Issue 3: Adapter Method Not Found

**Error:**
```
AttributeError: 'OpenAIClassifierAdapter' object has no attribute 'classify_material'
```

**Solution:**
Make sure you're using updated adapters from V4:
```python
# Check adapter has V4 method
from app.adapters.openai_adapter import OpenAIClassifierAdapter

adapter = OpenAIClassifierAdapter()
assert hasattr(adapter, 'classify_material'), "Adapter needs V4 update"
```

---

## Rollback Plan

If you need to rollback to V3:

1. **Code Rollback:**
   ```bash
   git checkout main  # Or your V3 branch
   git branch -D feature/v4-migration
   ```

2. **Environment Rollback:**
   ```bash
   # Remove V4 env vars
   unset ROBOFLOW_API_KEY
   unset ROBOFLOW_MODEL_ID
   ```

3. **Dependencies Rollback:**
   ```bash
   pip install -r requirements-v3.txt
   ```

---

## Performance Comparison

| Metric | V3 | V4 | Improvement |
|--------|----|----|-------------|
| **Average Latency** | 3.5s | 1.0s | 71% faster |
| **P95 Latency** | 5.0s | 1.5s | 70% faster |
| **Cost per Request** | $0.031 | $0.011 | 65% cheaper |
| **Accuracy (Material)** | 85% | 85% | Same |
| **Accuracy (Subtype)** | N/A | 80% | New feature |
| **Accuracy (Volume)** | N/A | 70% | New feature |

---

## Testing Your Migration

```bash
# Run V4 tests
pytest tests/unit/agents/test_pre_validator_v4.py -v
pytest tests/unit/agents/test_material_classifier.py -v
pytest tests/integration/test_classification_pipeline_v4.py -v

# Run performance tests
pytest tests/performance/ -v --benchmark

# Check coverage
pytest tests/ --cov=app/agents --cov-report=term
```

---

## Support

If you encounter issues during migration:

1. Check this guide's Common Issues section
2. Review the Architecture Spec V4: `/agents-specs/V4/architecture-spec-agents_v4.md`
3. Check test examples in `/tests/unit/` and `/tests/integration/`
4. Open an issue on GitHub with:
   - Error message
   - Code snippet
   - Environment details (Python version, dependencies)

---

## Timeline

**Recommended Migration Schedule:**

- **Week 1:** Update development environment, run tests
- **Week 2:** Migrate PreValidator
- **Week 3:** Migrate MaterialClassifier
- **Week 4:** Full integration testing
- **Week 5:** Deploy to staging
- **Week 6:** Deploy to production

**Deprecation Timeline:**

- **Day 0:** V4 released
- **Day 30:** V3 marked as deprecated
- **Day 60:** V3 support ends

---

**Version:** 1.0
**Date:** 2025-11-14
**Author:** Agent Hub Team
