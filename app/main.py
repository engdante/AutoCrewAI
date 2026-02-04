#!/usr/bin/env python3
"""
CrewAI GUI Application
Main entry point for the application.
"""

import tkinter as tk
from tkinterdnd2 import TkinterDnD
from app.gui_main import CrewAIGUI

def main():
    root = TkinterDnD.Tk()
    app = CrewAIGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()