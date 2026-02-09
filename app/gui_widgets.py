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

class ToolSelector(ttk.Frame):
    """A widget to select tools and insert their info into a target Text widget."""
    def __init__(self, parent, target_text_widget, tools_info, **kwargs):
        super().__init__(parent, **kwargs)
        self.target_text = target_text_widget
        self.tools_info = tools_info
        
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True)
        
        self.listbox = tk.Listbox(list_frame, height=6, font=("Segoe UI", 9))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for tool in self.tools_info.get('available_tools', []):
            self.listbox.insert(tk.END, tool['name'])
            
        self.listbox.bind("<Double-Button-1>", self.on_double_click)
        
    def on_double_click(self, event):
        selection = self.listbox.curselection()
        if not selection:
            return
            
        tool_name = self.listbox.get(selection[0])
        tool_desc = ""
        
        for tool in self.tools_info.get('available_tools', []):
            if tool['name'] == tool_name:
                tool_desc = tool['description']
                break
        
        if "Tool Description:" in tool_desc:
            tool_desc = tool_desc.split("Tool Description:")[-1].strip()
        tool_desc = tool_desc.split("\n")[0].strip()
        insertion_text = f"Use the '{tool_name}' tool to: {tool_desc}\n"
        self.target_text.insert(tk.INSERT, insertion_text)
        self.target_text.see(tk.INSERT)
        self.target_text.focus_set()