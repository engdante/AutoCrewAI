import tkinter as tk
from tkinter import ttk

def add_context_menu(widget):
    """Adds a context menu with cut, copy, paste, and select all options to a widget."""
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_command(label="Select All", command=lambda: widget.event_generate("<<SelectAll>>"))

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", show_menu)
    widget.bind("<Control-a>", lambda e: widget.event_generate("<<SelectAll>>"))
    widget.bind("<Control-A>", lambda e: widget.event_generate("<<SelectAll>>"))

def create_scrolled_text(parent, height, **kwargs):
    """Creates a scrolled text widget with context menu."""
    frame = ttk.Frame(parent)
    text = tk.Text(frame, height=height, font=("Segoe UI", 10), undo=True, padx=5, pady=5, **kwargs)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    text.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    add_context_menu(text)
    return frame, text