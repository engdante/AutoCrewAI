import sys
import os

def test_import():
    sys.path.append(os.getcwd())
    try:
        from script.tools_registry import get_available_tools
        info = get_available_tools()
        print(f"Success! Found {len(info['available_tools'])} tools.")
        for t in info['available_tools']:
            print(f" - {t['name']}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_import()
