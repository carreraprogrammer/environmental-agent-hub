"""Script to check Roboflow configuration and list workspaces."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from roboflow import Roboflow
from app.core.config import settings

def main():
    print(f"🔑 Using API Key: {settings.ROBOFLOW_API_KEY[:10]}...")
    print(f"📦 Model ID: {settings.ROBOFLOW_MODEL_ID}")
    print()
    
    try:
        rf = Roboflow(api_key=settings.ROBOFLOW_API_KEY)
        
        print("📋 Available workspaces:")
        print("-" * 60)
        
        # Try to get workspace info
        # Note: Roboflow API may not have a direct list_workspaces method
        # So we'll try with the workspace from the model_id
        
        parts = settings.ROBOFLOW_MODEL_ID.split("/")
        if len(parts) == 2:
            print(f"⚠️  Model ID format appears incorrect: {settings.ROBOFLOW_MODEL_ID}")
            print(f"   Expected format: workspace/project/version")
            print(f"   Your format: project/version")
            print()
            print("Please update your .env file with the correct format.")
            print("Example: ROBOFLOW_MODEL_ID=your-workspace/waste-classifier-louut-b9sot/1")
            print()
            print("To find your workspace:")
            print("1. Go to https://app.roboflow.com/")
            print("2. Look at the URL when viewing your project")
            print("3. It should be: https://app.roboflow.com/WORKSPACE/PROJECT/VERSION")
            
        elif len(parts) == 3:
            workspace_id, project_id, version = parts
            print(f"✓ Workspace: {workspace_id}")
            print(f"✓ Project: {project_id}")
            print(f"✓ Version: {version}")
            print()
            
            try:
                workspace = rf.workspace(workspace_id)
                print(f"✓ Workspace '{workspace_id}' found!")
                
                try:
                    project = workspace.project(project_id)
                    print(f"✓ Project '{project_id}' found!")
                    
                    try:
                        model = project.version(version).model
                        print(f"✓ Model version {version} found!")
                        print()
                        print("🎉 Configuration is correct!")
                    except Exception as e:
                        print(f"❌ Error loading model version: {e}")
                        
                except Exception as e:
                    print(f"❌ Error loading project: {e}")
                    
            except Exception as e:
                print(f"❌ Error loading workspace: {e}")
        else:
            print(f"❌ Invalid model ID format: {settings.ROBOFLOW_MODEL_ID}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Please check:")
        print("1. ROBOFLOW_API_KEY is valid")
        print("2. ROBOFLOW_MODEL_ID has format: workspace/project/version")

if __name__ == "__main__":
    main()
