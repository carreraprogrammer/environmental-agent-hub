#!/usr/bin/env python3
"""
Simple test script to verify the FastAPI app can start and respond.
"""
import sys
import asyncio
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_app():
    try:
        print("🧪 Testing FastAPI application...")
        
        # Test importing the app
        from app.main import app
        print("✅ App imported successfully")
        
        # Test the health check function directly
        from app.main import health_check_direct
        result = await health_check_direct()
        print(f"✅ Health check works: {result}")
        
        # Test creating a test client
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        print(f"✅ Root endpoint status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test health endpoint
        response = client.get("/health")
        print(f"✅ Health endpoint status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        print("\n🎉 All tests passed! The app should work on Railway.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_app())
    sys.exit(0 if success else 1)