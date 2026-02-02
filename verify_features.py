import sys
import os
sys.path.append(os.getcwd())

from app import CrewModel

def test_new_features():
    print("Testing Rename and Input Folder...")
    model = CrewModel()
    
    # 1. Test Input Folder Creation on New Crew
    test_crew = "InputTestCrew"
    if os.path.exists(os.path.join("crews", test_crew)):
        import shutil
        shutil.rmtree(os.path.join("crews", test_crew))
        
    model.create_new_crew(test_crew, "Testing input folder")
    
    input_path = os.path.join("crews", test_crew, "input")
    if os.path.exists(input_path):
        print(f"PASSED: Input folder created for {test_crew}")
    else:
        print(f"FAILED: Input folder missing for {test_crew}")

    # 2. Test Rename Crew
    rename_target = "RenamedCrew"
    if os.path.exists(os.path.join("crews", rename_target)):
        import shutil
        shutil.rmtree(os.path.join("crews", rename_target))
        
    success, msg = model.rename_crew(test_crew, rename_target)
    
    if success and msg == rename_target:
        print(f"PASSED: Renamed {test_crew} to {rename_target}")
        if os.path.exists(os.path.join("crews", rename_target)):
             print("PASSED: New folder exists")
        else:
             print("FAILED: New folder missing")
             
        if not os.path.exists(os.path.join("crews", test_crew)):
            print("PASSED: Old folder removed")
        else:
            print("FAILED: Old folder still exists")
            
        # Check if input folder persisted/moved
        if os.path.exists(os.path.join("crews", rename_target, "input")):
             print("PASSED: Input folder exists in renamed crew")
        else:
             print("FAILED: Input folder missing in renamed crew")

    else:
        print(f"FAILED: Rename returned {success}, {msg}")

    # Clean up
    import shutil
    if os.path.exists(os.path.join("crews", rename_target)):
        shutil.rmtree(os.path.join("crews", rename_target))

if __name__ == "__main__":
    test_new_features()
