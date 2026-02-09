import tkinter as tk
import os
import requests
from tkinter import ttk, messagebox
import threading
from tkinterdnd2 import DND_FILES, TkinterDnD
from .gui_models import CrewModel
from .gui_widgets import add_context_menu, create_scrolled_text, ToolSelector
from .gui_dialogs import open_new_crew_dialog, open_rename_crew_dialog, open_settings, open_generate_dialog
from .gui_file_handlers import add_input_files, remove_input_files, open_input_folder, refresh_input_files, copy_files_to_input, open_input_file
from .gui_helpers import get_python_exe, execute_run_crew, fetch_ollama_models, update_all_model_dropdowns, refresh_data, get_tools_info

class CrewAIGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CrewAI Config Manager")
        self.root.geometry("1100x900")
        
        self.model = CrewModel()
        
        # Configure Styles
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        self.style.configure("Section.TLabelframe", padding=10)
        self.style.configure("Section.TLabelframe.Label", font=("Segoe UI", 11, "bold"))

        self.agent_widgets = []
        self.task_widgets = []
        self.ollama_models = []
        self.debug_var = tk.BooleanVar(value=False)
        
        # Bind dialog methods
        self.open_new_crew_dialog = lambda: open_new_crew_dialog(self.root, self)
        self.open_rename_crew_dialog = lambda: open_rename_crew_dialog(self.root, self)
        self.open_settings = lambda: open_settings(self.root, self)
        self.open_generate_dialog = lambda: open_generate_dialog(self.root, self)
        self.execute_run_crew = lambda: execute_run_crew(self)
        self.fetch_ollama_models = lambda combobox=None, server=None, port=None: fetch_ollama_models(self, combobox, server, port)
        self.update_all_model_dropdowns = lambda: update_all_model_dropdowns(self)
        self.refresh_data = lambda: refresh_data(self)
        self.add_input_files = lambda: add_input_files(self)
        self.remove_input_files = lambda: remove_input_files(self)
        self.open_input_folder = lambda: open_input_folder(self)
        self.refresh_input_files = lambda: refresh_input_files(self)
        self.copy_files_to_input = lambda file_paths: copy_files_to_input(self, file_paths)
        self.open_input_file = lambda: open_input_file(self)

        self.create_widgets()
        
        # Auto-load logic
        self.auto_load()
        
        # Start monitoring
        self.update_monitor_stats()

    def create_widgets(self):
        # Main Layout
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True)

        # Toolbar at top (fixed)
        toolbar = ttk.Frame(self.main_container, padding=10)
        toolbar.pack(side="top", fill="x")
        
        # Crew Selection
        ttk.Label(toolbar, text="Crew:").pack(side="left", padx=(0, 5))
        self.crew_var = tk.StringVar()
        self.crew_combo = ttk.Combobox(toolbar, textvariable=self.crew_var, state="readonly", width=20)

        self.crew_combo.pack(side="left", padx=5)
        self.crew_combo.bind("<<ComboboxSelected>>", self.change_crew)
        
        ttk.Button(toolbar, text="+ New", command=self.open_new_crew_dialog, width=6).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Rename", command=self.open_rename_crew_dialog, width=8).pack(side="left", padx=2)

        # Toolbar separators
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=10)

        # Toolbar buttons
        ttk.Button(toolbar, text="Refresh", command=self.refresh_data).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Save All", command=self.save_all).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Generate", command=self.open_generate_dialog).pack(side="left", padx=5)
        
        self.settings_btn = ttk.Button(toolbar, text="Settings", command=self.open_settings)
        self.settings_btn.pack(side="left", padx=5)

        # Debug Checkbox
        self.debug_check = ttk.Checkbutton(toolbar, text="Debug", variable=self.debug_var)
        self.debug_check.pack(side="left", padx=10)

        # Run Crew Button (Right Aligned)
        ttk.Button(toolbar, text="▶ Run Crew", command=self.execute_run_crew).pack(side="right", padx=5)

        # Crew Info Area (Description & Architecture)
        self.info_frame = ttk.Frame(self.main_container, padding=(20, 5))
        self.info_frame.pack(side="top", fill="x")
        
        self.desc_label = ttk.Label(self.info_frame, text="", font=("Segoe UI", 10, "italic"), foreground="#555")
        self.desc_label.pack(side="left")
        
        self.arch_label = ttk.Label(self.info_frame, text="", font=("Segoe UI", 9, "bold"))
        self.arch_label.pack(side="right")

        # Scrollable area
        self.canvas_frame = ttk.Frame(self.main_container)
        self.canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_content = ttk.Frame(self.canvas)
        self.content_window = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")

        self.scrollable_content.columnconfigure(0, weight=1)

        # Binds
        self.scrollable_content.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Global mousewheel binds
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel)
        self.root.bind_all("<Button-5>", self._on_mousewheel)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True, padx=20)
        self.scrollbar.pack(side="right", fill="y")

        # --- CONTENT SECTIONS ---
        
        # Agents Section
        ttk.Label(self.scrollable_content, text="Agents", style="Header.TLabel").pack(anchor="w", pady=(20, 10))
        self.agents_container = ttk.Frame(self.scrollable_content)
        self.agents_container.pack(fill="x", expand=True)
        self.agents_container.columnconfigure(0, weight=1)
        
        ttk.Button(self.scrollable_content, text="+ Add Agent", command=self.add_agent_row).pack(anchor="w", pady=10)

        # Tasks Section
        ttk.Label(self.scrollable_content, text="Tasks", style="Header.TLabel").pack(anchor="w", pady=(20, 10))
        self.tasks_container = ttk.Frame(self.scrollable_content)
        self.tasks_container.pack(fill="x", expand=True)
        self.tasks_container.columnconfigure(0, weight=1)
        
        ttk.Button(self.scrollable_content, text="+ Add Task", command=self.add_task_row).pack(anchor="w", pady=10)

        # Files Management Section
        ttk.Label(self.scrollable_content, text="Files Management", style="Header.TLabel").pack(anchor="w", pady=(20, 10))
        
        files_main_frame = ttk.Frame(self.scrollable_content)
        files_main_frame.pack(fill="x", expand=True, pady=(0, 10))
        files_main_frame.columnconfigure(0, weight=1)
        files_main_frame.columnconfigure(1, weight=1)

        # --- LEFT COLUMN: INPUT FILES ---
        input_frame = ttk.LabelFrame(files_main_frame, text="Input Files", style="Section.TLabelframe")
        input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Drag and Drop Zone
        self.drop_canvas = tk.Canvas(input_frame, height=100, bg="#f0f8ff", highlightthickness=2, highlightbackground="#b0c4de", relief="solid")
        self.drop_canvas.pack(fill="x", padx=10, pady=10)
        
        self.drop_zone_label = self.drop_canvas.create_text(
            10, 10,
            text="Drag & Drop files here\n",
            font=("Segoe UI", 10),
            fill="#808387",
            anchor="nw",
            width=300
        )

        self.drop_canvas.drop_target_register(DND_FILES)
        self.drop_canvas.dnd_bind('<<Drop>>', self.on_drop)
        self.drop_canvas.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        self.drop_canvas.dnd_bind('<<DragLeave>>', self.on_drag_leave)
        
        self.drop_zone_original_bg = "#f0f8ff"
        self.drop_zone_hover_bg = "#e6f2ff"

        # Input Buttons
        input_btn_frame = ttk.Frame(input_frame)
        input_btn_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(input_btn_frame, text="+ Add", width=8, command=self.add_input_files).pack(side="left", padx=(0, 2))
        ttk.Button(input_btn_frame, text="📄 Open", width=8, command=self.open_input_file).pack(side="left", padx=2)
        ttk.Button(input_btn_frame, text="🗑 Del", width=8, command=self.remove_input_files).pack(side="left", padx=2)
        ttk.Button(input_btn_frame, text="📂 Open Folder", command=self.open_input_folder).pack(side="left", padx=2)
        ttk.Button(input_btn_frame, text="🔄 Refresh", command=self.refresh_input_files).pack(side="left", padx=2)

        # Input Listbox
        self.files_listbox = tk.Listbox(input_frame, height=8, font=("Consolas", 9), selectmode=tk.EXTENDED)
        input_scrollbar = ttk.Scrollbar(input_frame, orient="vertical", command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=input_scrollbar.set)
        
        self.files_listbox.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        input_scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)
        
        # Bind double click to open file
        self.files_listbox.bind("<Double-Button-1>", lambda e: self.open_input_file())

        # --- RIGHT COLUMN: OUTPUT FILES ---
        output_frame = ttk.LabelFrame(files_main_frame, text="Output Files", style="Section.TLabelframe")
        output_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Output Buttons
        output_btn_frame = ttk.Frame(output_frame)
        output_btn_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(output_btn_frame, text="📄 Open File", command=self.open_output_file).pack(side="left", padx=(0, 5))
        ttk.Button(output_btn_frame, text="📂 Open Folder", command=self.open_output_folder).pack(side="left", padx=5)
        ttk.Button(output_btn_frame, text="🔄 Refresh", command=self.refresh_output_files).pack(side="left", padx=5)

        # Output Listbox
        self.output_files_listbox = tk.Listbox(output_frame, height=12, font=("Consolas", 9), selectmode=tk.EXTENDED)
        output_scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_files_listbox.yview)
        self.output_files_listbox.configure(yscrollcommand=output_scrollbar.set)
        
        self.output_files_listbox.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        output_scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)

        # Bind double click to open file
        self.output_files_listbox.bind("<Double-Button-1>", lambda e: self.open_output_file())

        # User Task Section
        user_task_header_frame = ttk.Frame(self.scrollable_content)
        user_task_header_frame.pack(fill="x", pady=(20, 0))
        user_task_header_frame.columnconfigure(0, weight=3)
        user_task_header_frame.columnconfigure(1, weight=1)

        ttk.Label(user_task_header_frame, text="User Task (Task.md)", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(user_task_header_frame, text="Tools").grid(row=0, column=1, sticky="w", padx=10)
        
        content_frame = ttk.Frame(self.scrollable_content)
        content_frame.pack(fill="x", pady=(5, 30))
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=1)

        self.user_task_text_frame = ttk.Frame(content_frame)
        self.user_task_text_frame.grid(row=0, column=0, sticky="nsew")
        
        self.user_task_text = tk.Text(self.user_task_text_frame, height=12, font=("Consolas", 11), padx=10, pady=10, undo=True)
        self.user_task_scrollbar = ttk.Scrollbar(self.user_task_text_frame, orient="vertical", command=self.user_task_text.yview)
        self.user_task_text.configure(yscrollcommand=self.user_task_scrollbar.set)
        
        self.user_task_text.pack(side="left", fill="both", expand=True)
        self.user_task_scrollbar.pack(side="right", fill="y")
        add_context_menu(self.user_task_text)

        # Tool Selector for User Task
        tools_info = get_tools_info()
        self.tool_selector = ToolSelector(content_frame, self.user_task_text, tools_info)
        self.tool_selector.grid(row=0, column=1, sticky="nsew", padx=10)

        # Status Bar for Monitoring
        self.status_bar = ttk.Frame(self.root, relief="sunken", padding=(10, 2))
        self.status_bar.pack(side="bottom", fill="x")
        
        self.monitor_label = ttk.Label(self.status_bar, text="Monitor: Initializing...", font=("Segoe UI", 9))
        self.monitor_label.pack(side="left")

        # Reset GPU Button
        self.reset_gpu_btn = ttk.Button(self.status_bar, text="🧹 Reset GPU (Clear VRAM)", 
                                        style="Small.TButton", command=self.reset_gpu_memory)
        self.reset_gpu_btn.pack(side="right", padx=5)
        
        # Add a small style for the status bar button
        self.style.configure("Small.TButton", font=("Segoe UI", 8))

    def reset_gpu_memory(self):
        """Attempts to clear Ollama VRAM by sending keep_alive: 0 for loaded models."""
        def reset_thread():
            server = os.getenv("OLLAMA_SERVER", "localhost").strip("'\"")
            port = os.getenv("OLLAMA_PORT", "11434").strip("'\"")
            
            try:
                # 1. Get list of tags (models)
                tags_url = f"http://{server}:{port}/api/tags"
                response = requests.get(tags_url, timeout=5)
                if response.status_code != 200:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Could not connect to Ollama at {tags_url}"))
                    return

                models = response.json().get('models', [])
                if not models:
                    self.root.after(0, lambda: messagebox.showinfo("Info", "No Ollama models found."))
                    return

                # 2. Try to unload the first model (usually sufficient to trigger a cleanup)
                # Or better, try to unload the currently selected model if available
                model_to_unload = models[0]['name']
                
                # Check if any agent has a model selected
                for a in self.agent_widgets:
                    if a['model'].get():
                        model_to_unload = a['model'].get()
                        break

                unload_url = f"http://{server}:{port}/api/generate"
                payload = {
                    "model": model_to_unload,
                    "keep_alive": 0
                }
                
                unload_res = requests.post(unload_url, json=payload, timeout=5)
                if unload_res.status_code == 200:
                    self.root.after(0, lambda: messagebox.showinfo("Success", f"Sent unload command for '{model_to_unload}'. VRAM should be clearing..."))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to unload model: {unload_res.status_code}"))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Reset failed: {str(e)}"))

        threading.Thread(target=reset_thread, daemon=True).start()

    # --- Monitoring Logic ---
    def update_monitor_stats(self):
        """Fetch system stats from the monitor server and update the status bar"""
        def fetch_thread():
            server = os.getenv("OLLAMA_SERVER", "192.168.110.158").strip("'\"")
            port = os.getenv("MONITOR_PORT", "5000").strip("'\"")
            url = f"http://{server}:{port}/stats/summary"
            try:
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    parts = []
                    parts.append(f"CPU: {data.get('cpu_usage', 'N/A')}")
                    parts.append(f"RAM: {data.get('ram_usage', 'N/A')}")
                    parts.append(f"Disk: {data.get('disk_usage', 'N/A')}")
                    
                    # Check for GPUs
                    gpu_idx = 0
                    while f'gpu_{gpu_idx}_usage' in data:
                        parts.append(f"GPU{gpu_idx}: {data[f'gpu_{gpu_idx}_usage']} (VRAM: {data[f'gpu_{gpu_idx}_vram']})")
                        gpu_idx += 1
                        
                    if 'ollama_models' in data:
                        parts.append(f"Models: {data['ollama_models']}")
                    
                    text = " | ".join(parts)
                    self.root.after(0, lambda: self.monitor_label.config(text=text, foreground="black"))
                else:
                    self.root.after(0, lambda: self.monitor_label.config(text=f"Monitor: HTTP {response.status_code} ({url})", foreground="orange"))
            except requests.exceptions.Timeout:
                self.root.after(0, lambda: self.monitor_label.config(text=f"Monitor: Timeout ({url})", foreground="red"))
            except requests.exceptions.ConnectionError:
                self.root.after(0, lambda: self.monitor_label.config(text=f"Monitor: Connection Refused ({url})", foreground="red"))
            except Exception as e:
                self.root.after(0, lambda: self.monitor_label.config(text=f"Monitor: Error {type(e).__name__} ({url})", foreground="red"))
            
            # Schedule next update in 2 seconds (to avoid spamming)
            self.root.after(2000, self.update_monitor_stats)

        threading.Thread(target=fetch_thread, daemon=True).start()

    # --- Scroll & Resize Logic ---
    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.content_window, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    # --- Row Management ---
    def auto_load(self):
        # Load Crews
        crews = self.model.get_crews()
        self.crew_combo['values'] = crews
        if self.model.current_crew_name in crews:
            self.crew_combo.set(self.model.current_crew_name)
        elif crews:
            self.crew_combo.current(0)
            self.change_crew(None) # Trigger load

        self.model.load_data()
        
        # Update Info Labels
        self.desc_label.config(text=self.model.description)
        arch_text = f"Architecture: {self.model.architecture}"
        if self.model.supervisor_agent != "None":
            arch_text += f" | Supervisor: {self.model.supervisor_agent}"
        self.arch_label.config(text=arch_text)

        # Populate Agents
        if self.model.agents:
            for agent in self.model.agents:
                self.add_agent_row(agent)
        else:
            self.add_agent_row() # Empty default

        # Populate Tasks
        if self.model.tasks:
            for task in self.model.tasks:
                self.add_task_row(task)
        else:
            self.add_task_row() # Empty default

        # Populate User Task
        user_task = self.model.load_task()
        self.user_task_text.delete("1.0", tk.END)
        self.user_task_text.insert("1.0", user_task)
        
        # Set Debug Var
        self.debug_var.set(self.model.debug_enabled)
        
        self.update_agent_dropdowns()
        
        # Refresh input files list
        self.refresh_input_files()
        self.refresh_output_files()

    def change_crew(self, event):
        new_crew = self.crew_combo.get()
        if new_crew and new_crew != self.model.current_crew_name:
            self.model.set_active_crew(new_crew)
            self.refresh_data()

    def add_agent_row(self, data=None):
        frame = ttk.LabelFrame(self.agents_container, text="Agent Details", style="Section.TLabelframe")
        frame.pack(fill="x", pady=5, expand=True)
        
        frame.columnconfigure(0, minsize=120)
        frame.columnconfigure(1, weight=1)

        # Name
        ttk.Label(frame, text="Name:").grid(row=0, column=0, sticky="e", padx=(5, 10), pady=1)
        name_var = tk.StringVar(value=data['name'] if data else "")
        name_entry = ttk.Entry(frame, textvariable=name_var)
        name_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=1)
        name_var.trace_add("write", lambda *args: self.update_agent_dropdowns())
        add_context_menu(name_entry)

        # Role
        ttk.Label(frame, text="Role:").grid(row=1, column=0, sticky="e", padx=(5, 10), pady=1)
        role_entry = ttk.Entry(frame)
        role_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=1)
        if data: role_entry.insert(0, data['role'])
        add_context_menu(role_entry)

        # Goal
        ttk.Label(frame, text="Goal:").grid(row=2, column=0, sticky="e", padx=(5, 10), pady=1)
        goal_entry = ttk.Entry(frame)
        goal_entry.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=1)
        if data: goal_entry.insert(0, data['goal'])
        add_context_menu(goal_entry)

        # Backstory
        ttk.Label(frame, text="Backstory:").grid(row=3, column=0, sticky="ne", padx=(5, 10), pady=10)
        backstory_frame, backstory_text = create_scrolled_text(frame, height=4)
        backstory_frame.grid(row=3, column=1, sticky="ew", padx=(0, 10), pady=10)
        if data: backstory_text.insert("1.0", data['backstory'])

        # Model
        ttk.Label(frame, text="Model:").grid(row=4, column=0, sticky="e", padx=(5, 10), pady=1)
        model_frame = ttk.Frame(frame)
        model_frame.grid(row=4, column=1, sticky="ew", padx=(0, 10), pady=1)
        
        # Start with fetched models + current model if loaded
        initial_models = list(self.ollama_models)
        if data and data['model'] and data['model'] not in initial_models:
            initial_models.insert(0, data['model'])
            
        model_entry = ttk.Combobox(model_frame, values=initial_models)
        model_entry.pack(side="left", fill="x", expand=True)
        
        if data: 
            model_entry.set(data['model'])
        elif self.ollama_models:
            model_entry.set(self.ollama_models[0])
            
        refresh_btn = ttk.Button(model_frame, text="↻", width=3, 
                               command=lambda e=model_entry: self.fetch_ollama_models(e))
        refresh_btn.pack(side="right", padx=(5, 0))

        # Web Search Checkbox
        ws_var = tk.BooleanVar(value=data.get('web_search', False) if data else False)
        ws_check = ttk.Checkbutton(model_frame, text="Web Search", variable=ws_var)
        ws_check.pack(side="right", padx=(10, 5))

        add_context_menu(model_entry)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, sticky="e", pady=2)
        
        agent_item = {
            'frame': frame,
            'name_var': name_var,
            'role': role_entry,
            'goal': goal_entry,
            'backstory': backstory_text,
            'model': model_entry,
            'web_search_var': ws_var
        }
        
        ttk.Button(btn_frame, text="Remove Agent", command=lambda: self.remove_agent(agent_item)).pack(padx=10)
        self.agent_widgets.append(agent_item)
        self.root.update_idletasks()

    def remove_agent(self, agent_item):
        if len(self.agent_widgets) <= 1:
            messagebox.showwarning("Warning", "At least one agent is required.")
            return
        self.agent_widgets.remove(agent_item)
        agent_item['frame'].destroy()
        self.update_agent_dropdowns()
        self.root.update_idletasks()

    def add_task_row(self, data=None):
        frame = ttk.LabelFrame(self.tasks_container, text="Task Details", style="Section.TLabelframe")
        frame.pack(fill="x", pady=5, expand=True)
        
        frame.columnconfigure(0, minsize=120)
        frame.columnconfigure(1, weight=3)
        frame.columnconfigure(3, weight=1)

        ttk.Label(frame, text="Task Name:").grid(row=0, column=0, sticky="e", padx=(5, 10), pady=1)
        name_entry = ttk.Entry(frame)
        name_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=1)
        if data: name_entry.insert(0, data['name'])
        add_context_menu(name_entry)

        ttk.Label(frame, text="Output File:").grid(row=0, column=2, sticky="e", padx=(10, 5), pady=1)
        output_entry = ttk.Entry(frame)
        output_entry.grid(row=0, column=3, sticky="ew", padx=(0, 10), pady=1)
        if data: output_entry.insert(0, data['output_file'])
        add_context_menu(output_entry)

        ttk.Label(frame, text="Description:").grid(row=1, column=0, sticky="ne", padx=(5, 10), pady=10)
        desc_frame, desc_text = create_scrolled_text(frame, height=3)
        desc_frame.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(0, 10), pady=10)
        if data: desc_text.insert("1.0", data['description'])

        ttk.Label(frame, text="Expected Output:").grid(row=2, column=0, sticky="e", padx=(5, 10), pady=1)
        expected_entry = ttk.Entry(frame)
        expected_entry.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(0, 10), pady=1)
        if data: expected_entry.insert(0, data['expected_output'])
        add_context_menu(expected_entry)

        ttk.Label(frame, text="Assigned Agent:").grid(row=3, column=0, sticky="e", padx=(5, 10), pady=1)
        agent_var = tk.StringVar()
        agent_combo = ttk.Combobox(frame, textvariable=agent_var, state="readonly")
        agent_combo.grid(row=3, column=1, sticky="w", padx=(0, 10), pady=1)
        if data: agent_var.set(data['agent'])

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=4, sticky="e", pady=2)
        
        task_item = {
            'frame': frame,
            'name': name_entry,
            'output_file': output_entry,
            'description': desc_text,
            'expected_output': expected_entry,
            'agent_var': agent_var,
            'agent_combo': agent_combo
        }
        
        ttk.Button(btn_frame, text="Remove Task", command=lambda: self.remove_task(task_item)).pack(padx=10)
        self.task_widgets.append(task_item)
        self.root.update_idletasks()

    def remove_task(self, task_item):
        if len(self.task_widgets) <= 1:
            messagebox.showwarning("Warning", "At least one task is required.")
            return
        self.task_widgets.remove(task_item)
        task_item['frame'].destroy()
        self.root.update_idletasks()

    def update_agent_dropdowns(self):
        agent_names = [a['name_var'].get() for a in self.agent_widgets if a['name_var'].get().strip()]
        for t in self.task_widgets:
            current_val = t['agent_var'].get()
            t['agent_combo']['values'] = agent_names
            if current_val in agent_names:
                t['agent_var'].set(current_val)

    def save_all(self):
        # Gather data
        agents_data = []
        for a in self.agent_widgets:
            agents_data.append({
                'name': a['name_var'].get().strip(),
                'role': a['role'].get().strip(),
                'goal': a['goal'].get().strip(),
                'backstory': a['backstory'].get('1.0', tk.END).strip(),
                'model': a['model'].get().strip(),
                'web_search': a['web_search_var'].get()
            })
            
        tasks_data = []
        for t in self.task_widgets:
            tasks_data.append({
                'name': t['name'].get().strip(),
                'output_file': t['output_file'].get().strip(),
                'description': t['description'].get('1.0', tk.END).strip(),
                'expected_output': t['expected_output'].get().strip(),
                'agent': t['agent_var'].get()
            })
            
        user_task_content = self.user_task_text.get("1.0", tk.END).strip()
        
        # Update model debug state before saving
        self.model.debug_enabled = self.debug_var.get()

        success = self.model.save_data(agents_data, tasks_data, user_task_content)
        if success:
            self.refresh_data()
            messagebox.showinfo("Success", "Saved Crew.md and Task.md successfully!")
        else:
            messagebox.showerror("Error", "Failed to save files. Check console for details.")

    # --- Drag and Drop Event Handlers ---
    
    def on_drag_enter(self, event):
        self.drop_canvas.config(bg=self.drop_zone_hover_bg, highlightbackground="#2196f3")
        self.root.update_idletasks()
    
    def on_drag_leave(self, event):
        self.drop_canvas.config(bg=self.drop_zone_original_bg, highlightbackground="#b0c4de")
        self.root.update_idletasks()
    
    def on_drop(self, event):
        self.drop_canvas.config(bg=self.drop_zone_original_bg, highlightbackground="#b0c4de")
        self.root.update_idletasks()
        
        data = event.data
        
        if not data:
            return
        
        if data.startswith('{') and data.endswith('}'):
            data = data[1:-1]
        
        files = [f.strip() for f in data.split('\0') if f.strip()]
        
        if len(files) == 1 and ' ' in files[0]:
            potential_files = files[0].split()
            if len(potential_files) > 1 and all(os.path.exists(f) for f in potential_files):
                files = potential_files
            
        if files:
            self.copy_files_to_input(files)

    # --- Output Files Logic ---
    def refresh_output_files(self):
        self.output_files_listbox.delete(0, tk.END)
        output_dir = os.path.join(self.model.current_crew_path, "output")
        
        if os.path.exists(output_dir):
            files = sorted(os.listdir(output_dir))
            for f in files:
                self.output_files_listbox.insert(tk.END, f)
                
    def open_output_file(self):
        selection = self.output_files_listbox.curselection()
        if not selection:
            return
            
        file_name = self.output_files_listbox.get(selection[0])
        file_path = os.path.join(self.model.current_crew_path, "output", file_name)
        
        if os.path.exists(file_path):
            try:
                os.startfile(file_path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
                
    def open_output_folder(self):
        output_dir = os.path.join(self.model.current_crew_path, "output")
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except: pass
            
        try:
            os.startfile(output_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")