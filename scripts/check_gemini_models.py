"""Script to check available Gemini models for your API key."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import google.generativeai as genai
from app.core.config import settings

def main():
    print(f"🔑 Using API Key: {settings.GOOGLE_API_KEY[:20]}...")
    print()
    
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        print("📋 Available models with generateContent support:")
        print("-" * 60)
        
        models_found = False
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                models_found = True
                print(f"✓ {model.name}")
                print(f"  Display Name: {model.display_name}")
                print(f"  Description: {model.description[:100]}...")
                print()
        
        if not models_found:
            print("❌ No models with generateContent support found!")
            print()
            print("Possible reasons:")
            print("1. API key is invalid or expired")
            print("2. Gemini API is not enabled for your account")
            print("3. Your account doesn't have access to Gemini models")
            print()
            print("Visit: https://makersuite.google.com/app/apikey")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("This usually means:")
        print("1. Invalid API key")
        print("2. Network issues")
        print("3. Gemini API not enabled")
        print()
        print("Get your API key at: https://makersuite.google.com/app/apikey")

if __name__ == "__main__":
    main()
