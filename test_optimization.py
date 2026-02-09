#!/usr/bin/env python3
"""
Test script for CrewAI optimization
Validates that the enhanced system works correctly
"""

import os
import sys
import tempfile
import shutil

# Add script directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

def test_crew_creation():
    """Test crew creation with the enhanced create_crew.py"""
    print("=== Testing Crew Creation ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Test command
        cmd = [
            sys.executable, 
            "script/create_crew.py",
            "Test task for crew creation",
            "--preview",  # Preview mode to avoid saving
            "--model", "llama3",
            "--architecture", "sequential"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Change to project root
        original_cwd = os.getcwd()
        os.chdir(SCRIPT_DIR)
        
        try:
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout[:1000] + "..." if len(result.stdout) > 1000 else result.stdout)
            
            if result.stderr:
                print("STDERR:")
                print(result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr)
            
            if result.returncode == 0:
                print("✅ Crew creation test passed!")
                return True
            else:
                print("❌ Crew creation test failed!")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Crew creation test timed out!")
            return False
        except Exception as e:
            print(f"❌ Crew creation test failed with error: {e}")
            return False
        finally:
            os.chdir(original_cwd)

def test_crew_parsing():
    """Test crew parsing with the enhanced run_crew.py"""
    print("\n=== Testing Crew Parsing ===")
    
    # Create a minimal valid Crew.md for testing
    test_crew_md = """# Crew Team: Test Crew

## Configuration
- Architecture: sequential
- Supervisor Agent: None

## Agents

### Test Agent
- **Role**: Test Role
- **Goal**: Test Goal
- **Backstory**: Test Backstory
- **Model**: llama3

## Tasks

### Test Task [Output: test_output.md]
- **Description**: This is a test task.
- **Expected Output**: Test output.
- **Agent**: Test Agent
"""

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Write test Crew.md
        crew_file = os.path.join(temp_dir, "Crew.md")
        task_file = os.path.join(temp_dir, "Task.md")
        
        with open(crew_file, 'w', encoding='utf-8') as f:
            f.write(test_crew_md)
        
        with open(task_file, 'w', encoding='utf-8') as f:
            f.write("# User Task for Agents\n\nThis is a test task.")
        
        # Test command
        cmd = [
            sys.executable,
            "script/run_crew.py",
            "--crew-file", crew_file,
            "--task-file", task_file,
            "--output-dir", temp_dir
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Change to project root
        original_cwd = os.getcwd()
        os.chdir(SCRIPT_DIR)
        
        try:
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print("STDOUT (first 500 chars):")
                print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            
            if result.stderr:
                print("STDERR (first 500 chars):")
                print(result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr)
            
            # Check if output files were created
            output_files = [f for f in os.listdir(temp_dir) if f.endswith('.md')]
            print(f"Output files created: {output_files}")
            
            if result.returncode == 0 and len(output_files) > 0:
                print("✅ Crew parsing test passed!")
                return True
            else:
                print("❌ Crew parsing test failed!")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Crew parsing test timed out!")
            return False
        except Exception as e:
            print(f"❌ Crew parsing test failed with error: {e}")
            return False
        finally:
            os.chdir(original_cwd)

def main():
    """Run all tests"""
    print("CrewAI Optimization Test Suite")
    print("=" * 50)
    
    tests = [
        ("Crew Creation", test_crew_creation),
        ("Crew Parsing", test_crew_parsing)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The CrewAI optimization is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)