
import tkinter as tk
from tkinter import messagebox
import sys

def show_confirmation_dialog(title, message):
    """
    Shows a simple OK/Cancel dialog.
    Returns True if OK was pressed, False otherwise.
    """
    root = tk.Tk()
    root.withdraw() # Hide the main window
    root.attributes("-topmost", True) # Make it stay on top
    
    result = messagebox.askokcancel(title, message)
    
    root.destroy()
    return result

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gui_utils.py <title> <message>")
        sys.exit(1)
        
    title = sys.argv[1]
    message = sys.argv[2]
    
    if show_confirmation_dialog(title, message):
        print("CONFIRMED")
        sys.exit(0)
    else:
        print("CANCELLED")
        sys.exit(1)
