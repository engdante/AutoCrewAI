import sys
import os
import tkinter as tk
from tkinter import ttk

sys.path.append(os.getcwd())

# Mock message box to avoid blocking
import tkinter.messagebox
def mock_showinfo(*args, **kwargs): print("showinfo", args); return
def mock_showwarning(*args, **kwargs): print("showwarning", args); return
def mock_showerror(*args, **kwargs): print("showerror", args); return
tkinter.messagebox.showinfo = mock_showinfo
tkinter.messagebox.showwarning = mock_showwarning
tkinter.messagebox.showerror = mock_showerror

from app import CrewAIGUI

def test_gui_attributes():
    print("Testing GUI attributes...")
    root = tk.Tk()
    # We don't want to actually show the window if possible, or close it quickly
    # But creating CrewAIGUI will trigger auto_load which calls change_crew
    # We just want to ensure it doesn't crash on init
    
    try:
        app = CrewAIGUI(root)
        print("CrewAIGUI initialized successfully.")
        
        if hasattr(app, 'change_crew'):
            print("Verified: change_crew exists.")
        else:
            print("FAILED: change_crew missing.")
            
        if hasattr(app, 'open_new_crew_dialog'):
            print("Verified: open_new_crew_dialog exists.")
        else:
            print("FAILED: open_new_crew_dialog missing.")
            
    except Exception as e:
        print(f"FAILED to initialize GUI: {e}")
    finally:
        root.destroy()

if __name__ == "__main__":
    test_gui_attributes()
