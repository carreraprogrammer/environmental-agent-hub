"""
Validation Script: Fast Path (Roboflow) vs Full Pipeline (Gemini)

Compares classification results between:
- Fast Path: Roboflow quick classification
- Full Pipeline: Gemini MaterialClassifier (ground truth)

Measures:
- Agreement rate
- Confidence differences
- Material-specific accuracy
- Mismatch patterns
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.fast_classifier import FastClassifier
from app.factories.classifier_factory import ClassifierFactory
from app.orchestrator.pipeline import Pipeline
from app.schemas.requests import ClassifyRequest
from app.schemas.domain import WasteMaterial
from app.core.logging import logger


class ValidationReport:
    """Generate comprehensive validation report."""
    
    def __init__(self):
        self.results = []
        self.total = 0
        self.agreements = 0
        self.mismatches = 0
        self.by_material = {}
    
    def add_result(self, image_name: str, fast_result: dict, full_result: dict):
        """Add a comparison result."""
        # fast_result is a dict with "material" (WasteMaterial enum), "confidence" (float), "color" (BinColor enum)
        fast_mat = fast_result["material"]  # WasteMaterial enum
        fast_conf = fast_result["confidence"]
        fast_color = fast_result["color"]  # BinColor enum
        
        # full_result is ValidationResult with .material (WasteMaterial enum), .confidence (float), .color (BinColor enum)
        validated_mat = full_result.material
        validated_conf = full_result.confidence
        validated_color = full_result.color
        
        # Compare enums directly
        agreement = fast_mat == validated_mat
        
        result = {
            "image": image_name,
            "fast_material": fast_mat.value,  # Store string value for display
            "fast_confidence": fast_conf,
            "validated_material": validated_mat.value,  # Store string value for display
            "validated_confidence": validated_conf,
            "agreement": agreement,
            "confidence_diff": abs(fast_conf - validated_conf),
            "fast_color": fast_color.value,  # Store string value for display
            "validated_color": validated_color.value,  # Store string value for display
        }
        
        self.results.append(result)
        self.total += 1
        
        if agreement:
            self.agreements += 1
        else:
            self.mismatches += 1
        
        # Track by material (use string value for dict key)
        mat_key = validated_mat.value
        if mat_key not in self.by_material:
            self.by_material[mat_key] = {
                "total": 0,
                "correct": 0,
                "incorrect": 0
            }
        
        self.by_material[mat_key]["total"] += 1
        if agreement:
            self.by_material[mat_key]["correct"] += 1
        else:
            self.by_material[mat_key]["incorrect"] += 1
    
    def print_report(self):
        """Print comprehensive validation report."""
        print("\n" + "=" * 100)
        print("📊 FAST PATH VALIDATION REPORT - Roboflow vs Gemini")
        print("=" * 100)
        
        # Overall statistics
        print("\n1️⃣ Overall Statistics:")
        print(f"   • Total images classified: {self.total}")
        
        if self.total == 0:
            print("   ⚠️ No images were successfully classified by both systems")
            return
        
        print(f"   • Agreements: {self.agreements}/{self.total} ({self.agreements/self.total*100:.1f}%)")
        print(f"   • Mismatches: {self.mismatches}/{self.total} ({self.mismatches/self.total*100:.1f}%)")
        
        agreement_rate = (self.agreements / self.total * 100)
        if agreement_rate >= 85:
            status = "✅ EXCELLENT"
        elif agreement_rate >= 70:
            status = "⚠️ ACCEPTABLE"
        else:
            status = "❌ NEEDS IMPROVEMENT"
        
        print(f"   • Status: {status} (target: >85%)")
        
        # Per-material accuracy
        print("\n2️⃣ Accuracy by Material (Ground Truth):")
        print(f"{'Material':<15} {'Total':<8} {'Correct':<10} {'Incorrect':<12} {'Accuracy':<10}")
        print("-" * 100)
        
        for material, stats in sorted(self.by_material.items()):
            accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            status_icon = "✅" if accuracy >= 85 else "⚠️" if accuracy >= 70 else "❌"
            print(f"{material:<15} {stats['total']:<8} {stats['correct']:<10} {stats['incorrect']:<12} {accuracy:>6.1f}% {status_icon}")
        
        # Individual results
        print("\n3️⃣ Individual Classification Results:")
        print(f"{'Image':<30} {'Fast':<12} {'Validated':<12} {'Agreement':<12} {'Conf Diff':<12} {'Colors':<20}")
        print("-" * 100)
        
        for r in self.results:
            agreement_icon = "✅" if r["agreement"] else "❌"
            color_match = "✅" if r["fast_color"] == r["validated_color"] else "❌"
            colors = f"{r['fast_color']} → {r['validated_color']} {color_match}"
            
            print(f"{r['image']:<30} {r['fast_material']:<12} {r['validated_material']:<12} "
                  f"{agreement_icon:<12} {r['confidence_diff']:>6.2f}     {colors:<20}")
        
        # Mismatch analysis
        if self.mismatches > 0:
            print("\n4️⃣ Mismatch Patterns:")
            mismatches = [r for r in self.results if not r["agreement"]]
            
            # Group by fast material
            by_fast_mat = {}
            for m in mismatches:
                fast_mat = m["fast_material"]
                if fast_mat not in by_fast_mat:
                    by_fast_mat[fast_mat] = []
                by_fast_mat[fast_mat].append(m["validated_material"])
            
            for fast_mat, validated_mats in by_fast_mat.items():
                print(f"\n   Roboflow classified as {fast_mat}:")
                for val_mat in set(validated_mats):
                    count = validated_mats.count(val_mat)
                    print(f"      → Actually {val_mat}: {count} time(s)")
        
        # Recommendations
        print("\n5️⃣ Recommendations:")
        
        if agreement_rate >= 85:
            print("   ✅ Roboflow model is performing well!")
            print("   ✅ Safe to deploy Fast Path to production")
            print("   💡 Continue monitoring agreement rate in production")
        elif agreement_rate >= 70:
            print("   ⚠️ Roboflow model has acceptable accuracy")
            print("   💡 Consider retraining with more examples of misclassified materials")
            print("   💡 Monitor closely in production, be ready to rollback")
        else:
            print("   ❌ Roboflow model needs significant improvement")
            print("   ❌ DO NOT deploy Fast Path until model is retrained")
            print("   💡 Collect more training data for all material types")
            print("   💡 Focus on materials with lowest accuracy")
        
        # Confidence analysis
        avg_conf_diff = sum(r["confidence_diff"] for r in self.results) / len(self.results)
        print(f"\n6️⃣ Confidence Analysis:")
        print(f"   • Average confidence difference: {avg_conf_diff:.3f}")
        print(f"   • Roboflow avg confidence: {sum(r['fast_confidence'] for r in self.results) / len(self.results):.3f}")
        print(f"   • Gemini avg confidence: {sum(r['validated_confidence'] for r in self.results) / len(self.results):.3f}")
        
        print("\n" + "=" * 100)
        print("✅ Validation Complete")
        print("=" * 100)


async def classify_with_fast_path(image_path: Path, fast_classifier: FastClassifier) -> dict:
    """Classify image using Fast Path (Roboflow)."""
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    trace_id = str(uuid4())
    result = await fast_classifier.classify_fast(image_data, trace_id)
    
    return result


async def classify_with_full_pipeline(image_path: Path, pipeline: Pipeline) -> dict:
    """Classify image using Full Pipeline (Gemini)."""
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    trace_id = str(uuid4())
    
    # Use classifier.classify() which calls the adapter's classify_material
    result = await pipeline.classifier.classify(image_data, trace_id)
    
    # Result is MaterialClassificationResult
    # Extract material and confidence
    from app.utils.classification.color_mapper import ColorMapper
    color_mapper = ColorMapper()
    
    # Create simple result object with needed fields
    class ValidationResult:
        def __init__(self, mat_result):
            self.material = mat_result.material.material_type  # This is a WasteMaterial enum
            self.confidence = mat_result.material.confidence
            self.color = color_mapper.map_to_color(self.material, trace_id)
    
    return ValidationResult(result)


async def validate_images():
    """Validate multiple images comparing Fast Path vs Full Pipeline."""
    
    print("=" * 100)
    print("🔬 FAST PATH VALIDATION - Comparing Roboflow vs Gemini")
    print("=" * 100)
    print()
    
    # Initialize components
    print("⚙️  Initializing classifiers...")
    
    # Fast Path (Roboflow)
    roboflow_adapter = ClassifierFactory.create("roboflow")
    fast_classifier = FastClassifier(roboflow_adapter)
    
    # Full Pipeline (Gemini)
    pipeline = Pipeline()
    
    print("✅ Classifiers initialized")
    print()
    
    # Find test images
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "images"
    image_paths = list(fixtures_dir.glob("*.jpg")) + list(fixtures_dir.glob("*.jpeg")) + list(fixtures_dir.glob("*.png"))
    
    if not image_paths:
        print("❌ No test images found in tests/fixtures/images/")
        return
    
    print(f"📁 Found {len(image_paths)} test images")
    print()
    
    # Process each image
    report = ValidationReport()
    
    for idx, image_path in enumerate(image_paths, 1):
        print(f"🖼️  Processing {idx}/{len(image_paths)}: {image_path.name}")
        
        try:
            # Fast Path classification
            print(f"   ⚡ Fast Path (Roboflow)...", end=" ", flush=True)
            fast_result = await classify_with_fast_path(image_path, fast_classifier)
            print(f"→ {fast_result['material']} ({fast_result['confidence']:.2f})")
            
            # Full Pipeline classification
            print(f"   🔄 Full Pipeline (Gemini)...", end=" ", flush=True)
            full_result = await classify_with_full_pipeline(image_path, pipeline)
            print(f"→ {full_result.material.value} ({full_result.confidence:.2f})")
            
            # Compare
            agreement = fast_result["material"] == full_result.material.value
            status = "✅ MATCH" if agreement else "❌ MISMATCH"
            print(f"   {status}")
            
            # Add to report
            report.add_result(image_path.name, fast_result, full_result)
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            logger.error("validation_error", image=image_path.name, error=str(e))
        
        print()
    
    # Print comprehensive report
    report.print_report()


if __name__ == "__main__":
    asyncio.run(validate_images())
