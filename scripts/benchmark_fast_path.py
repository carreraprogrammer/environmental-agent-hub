"""
Benchmark script for Fast Path performance measurement.

Measures:
1. First request (cold start with Roboflow warmup)
2. Subsequent requests (warmed up)
3. Average latency after warmup
4. Backend sync completion time
"""

import asyncio
import time
from pathlib import Path
from uuid import uuid4

import httpx

# Configuration
BASE_URL = "http://localhost:8000"
NUM_REQUESTS = 5
IMAGE_PATH = Path(__file__).parent.parent / "tests" / "fixtures" / "images" / "pet_bottle.jpg"


async def send_classification_request(client: httpx.AsyncClient, request_num: int) -> dict:
    """Send a single classification request."""
    scan_id = str(uuid4())
    trace_id = str(uuid4())
    
    with open(IMAGE_PATH, "rb") as f:
        image_bytes = f.read()
    
    start_time = time.time()
    
    response = await client.post(
        f"{BASE_URL}/api/v1/classify",
        files={"image": ("pet_bottle.jpg", image_bytes, "image/jpeg")},
        data={
            "scan_id": scan_id,
            "station_id": f"BENCH-{request_num}",
            "tenant_id": "benchmark",
            "trace_id": trace_id,
        },
        timeout=30.0,
    )
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    if response.status_code != 200:
        print(f"❌ Request {request_num} failed: {response.status_code}")
        return None
    
    data = response.json()
    return {
        "request_num": request_num,
        "trace_id": trace_id,
        "total_latency_ms": elapsed_ms,
        "pipeline_latency_ms": data["meta"]["latency_ms"],
        "material": data["material"],
        "confidence": data["confidence"],
        "color": data["color"],
        "fast_mode": data["meta"].get("fast_mode", False),
        "validation_status": data["meta"].get("validation_status", "unknown"),
    }


async def benchmark():
    """Run benchmark with multiple requests."""
    print("=" * 80)
    print("🚀 FAST PATH BENCHMARK - Multiple Requests")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  • Requests: {NUM_REQUESTS}")
    print(f"  • Image: {IMAGE_PATH.name} ({IMAGE_PATH.stat().st_size} bytes)")
    print(f"  • Endpoint: {BASE_URL}/api/v1/classify")
    print(f"  • Fast Path: ENABLED (via env var)")
    print()
    
    results = []
    
    async with httpx.AsyncClient() as client:
        # Send requests sequentially to measure warmup effect
        for i in range(1, NUM_REQUESTS + 1):
            print(f"📡 Sending request {i}/{NUM_REQUESTS}...", end=" ", flush=True)
            
            result = await send_classification_request(client, i)
            
            if result:
                results.append(result)
                print(f"✅ {result['total_latency_ms']}ms")
            else:
                print("❌ Failed")
            
            # Small delay between requests
            await asyncio.sleep(0.5)
    
    if not results:
        print("\n❌ No successful requests. Check if server is running.")
        return
    
    # Analysis
    print("\n" + "=" * 80)
    print("📊 RESULTS ANALYSIS")
    print("=" * 80)
    
    # Individual results
    print("\n1️⃣ Individual Request Latencies:")
    print(f"{'Request':<10} {'Total (ms)':<12} {'Pipeline (ms)':<15} {'Material':<10} {'Fast Mode':<12}")
    print("-" * 80)
    
    for r in results:
        fast_indicator = "⚡ Yes" if r["fast_mode"] else "🐌 No"
        print(f"{r['request_num']:<10} {r['total_latency_ms']:<12} {r['pipeline_latency_ms']:<15} {r['material']:<10} {fast_indicator:<12}")
    
    # Statistics
    print("\n2️⃣ Latency Statistics:")
    
    first_request = results[0]
    subsequent_requests = results[1:] if len(results) > 1 else []
    
    print(f"\n🥶 Cold Start (Request #1):")
    print(f"   • Total latency: {first_request['total_latency_ms']}ms")
    print(f"   • Pipeline latency: {first_request['pipeline_latency_ms']}ms")
    print(f"   • Overhead: {first_request['total_latency_ms'] - first_request['pipeline_latency_ms']}ms")
    
    if subsequent_requests:
        avg_total = sum(r['total_latency_ms'] for r in subsequent_requests) / len(subsequent_requests)
        avg_pipeline = sum(r['pipeline_latency_ms'] for r in subsequent_requests) / len(subsequent_requests)
        min_total = min(r['total_latency_ms'] for r in subsequent_requests)
        max_total = max(r['total_latency_ms'] for r in subsequent_requests)
        
        print(f"\n🔥 Warmed Up (Requests #2-{NUM_REQUESTS}):")
        print(f"   • Average total: {avg_total:.0f}ms")
        print(f"   • Average pipeline: {avg_pipeline:.0f}ms")
        print(f"   • Min: {min_total}ms")
        print(f"   • Max: {max_total}ms")
        print(f"   • Range: {max_total - min_total}ms")
        
        # Improvement
        improvement = ((first_request['total_latency_ms'] - avg_total) / first_request['total_latency_ms']) * 100
        print(f"\n⚡ Warmup Improvement:")
        print(f"   • First request: {first_request['total_latency_ms']}ms")
        print(f"   • Warmed average: {avg_total:.0f}ms")
        print(f"   • Improvement: {improvement:.1f}% faster")
        print(f"   • Time saved: {first_request['total_latency_ms'] - avg_total:.0f}ms")
    
    # Target comparison
    print("\n3️⃣ Target Comparison:")
    
    if subsequent_requests:
        target_latency = 1000  # <1s target
        avg = avg_total
        
        print(f"   • Target: <{target_latency}ms")
        print(f"   • Actual (warmed): {avg:.0f}ms")
        
        if avg < target_latency:
            print(f"   • Status: ✅ ACHIEVED ({target_latency - avg:.0f}ms under target)")
        else:
            print(f"   • Status: ❌ MISSED ({avg - target_latency:.0f}ms over target)")
            print(f"   • Gap: {((avg / target_latency) - 1) * 100:.1f}% slower than target")
    
    # Fast mode verification
    print("\n4️⃣ Fast Mode Status:")
    fast_mode_count = sum(1 for r in results if r.get("fast_mode"))
    print(f"   • Fast mode used: {fast_mode_count}/{len(results)} requests ({fast_mode_count/len(results)*100:.0f}%)")
    print(f"   • Validation scheduled: {fast_mode_count} requests")
    
    # Material classification
    print("\n5️⃣ Classification Results:")
    materials = {}
    for r in results:
        mat = r["material"]
        materials[mat] = materials.get(mat, 0) + 1
    
    for material, count in materials.items():
        print(f"   • {material}: {count}/{len(results)} ({count/len(results)*100:.0f}%)")
    
    print("\n" + "=" * 80)
    print("✅ Benchmark Complete")
    print("=" * 80)
    
    # Summary recommendations
    if subsequent_requests and avg_total < 1000:
        print("\n💡 RECOMMENDATION: Fast Path is achieving target latency (<1s) after warmup!")
    elif subsequent_requests:
        print("\n💡 RECOMMENDATION: Consider further optimizations to reach <1s target:")
        print("   • Remove temporary file I/O in Roboflow adapter")
        print("   • Use S3 URL instead of bytes")
        print("   • Optimize Roboflow model")


if __name__ == "__main__":
    asyncio.run(benchmark())
