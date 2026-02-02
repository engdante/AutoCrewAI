import sys
import os
sys.path.append(os.getcwd())

from app import CrewModel

def test_crew_model():
    print("Testing CrewModel...")
    model = CrewModel()
    
    # Test get_crews
    crews = model.get_crews()
    print(f"Available crews: {crews}")
    assert "default" in crews
    
    # Test set_active_crew
    model.set_active_crew("default")
    print(f"Active crew: {model.current_crew_name}")
    print(f"Crew file: {model.crew_file}")
    assert model.current_crew_name == "default"
    assert model.crew_file.endswith("crews\\default\\Crew.md")
    
    # Test create_new_crew
    test_crew_name = "TestCrew"
    if os.path.exists(os.path.join("crews", test_crew_name)):
        import shutil
        shutil.rmtree(os.path.join("crews", test_crew_name))
        
    success, msg = model.create_new_crew(test_crew_name, "This is a test crew")
    print(f"Create crew result: {success}, {msg}")
    assert success
    assert os.path.exists(os.path.join("crews", test_crew_name, "crew.json"))
    
    # Cleanup
    # shutil.rmtree(os.path.join("crews", test_crew_name))
    print("CrewModel tests passed!")

if __name__ == "__main__":
    test_crew_model()
