import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import re
import os
import requests
import threading
from dotenv import load_dotenv, set_key, find_dotenv

class CrewModel:
    def __init__(self):
        self.agents = []
        self.tasks = []
        self.crew_file = "Crew.md"
        self.task_file = "Task.md"

    def load_data(self):
        self.agents = []
        self.tasks = []
        self.load_crew()
        self.load_task()

    def load_crew(self):
        if not os.path.exists(self.crew_file):
            return

        try:
            with open(self.crew_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse Agents
            agents_part_match = re.search(r"## Agents(.*?)(## Tasks|$)", content, re.DOTALL)
            if agents_part_match:
                agents_str = agents_part_match.group(1)
                agent_matches = re.finditer(r"### (.*?)\n(.*?)(?=### |$)", agents_str, re.DOTALL)
                for m in agent_matches:
                    name = m.group(1).strip()
                    details = m.group(2)
                    
                    def find_d(p, t):
                        m = re.search(p, t)
                        return m.group(1).strip() if m else ""

                    self.agents.append({
                        'name': name,
                        'role': find_d(r"\*\*\s*Role\s*\*\*: (.*)", details),
                        'goal': find_d(r"\*\*\s*Goal\s*\*\*: (.*)", details),
                        'backstory': find_d(r"\*\*\s*Backstory\s*\*\*: (.*)", details),
                        'model': find_d(r"\*\*\s*Model\s*\*\*: (.*)", details)
                    })

            # Parse Tasks
            tasks_part_match = re.search(r"## Tasks(.*)", content, re.DOTALL)
            if tasks_part_match:
                tasks_str = tasks_part_match.group(1)
                task_matches = re.finditer(r"### (.*?)\n(.*?)(?=### |$)", tasks_str, re.DOTALL)
                for m in task_matches:
                    title_line = m.group(1).strip()
                    output_file = ""
                    name = title_line
                    out_m = re.search(r"\[Output: (.*?)\]", title_line)
                    if out_m:
                        output_file = out_m.group(1).strip()
                        name = re.sub(r"\[Output: .*?\]", "", title_line).strip()
                    
                    details = m.group(2)
                    def find_d(p, t):
                        m = re.search(p, t)
                        return m.group(1).strip() if m else ""

                    self.tasks.append({
                        'name': name,
                        'output_file': output_file,
                        'description': find_d(r"\*\*\s*Description\s*\*\*: (.*)", details),
                        'expected_output': find_d(r"\*\*\s*Expected Output\s*\*\*: (.*)", details),
                        'agent': find_d(r"\*\*\s*Agent\s*\*\*: (.*)", details)
                    })
        except Exception as e:
            print(f"Error loading crew file: {e}")

    def load_task(self):
        if not os.path.exists(self.task_file):
            return ""
        
        try:
            with open(self.task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            # Clean up header if present
            content = re.sub(r"^\s*# User Task for Agents\s*\n*", "", content, flags=re.IGNORECASE | re.MULTILINE).strip()
            return content
        except Exception as e:
            print(f"Error loading task file: {e}")
            return ""

    def save_data(self, agents_data, tasks_data, user_task_content):
        try:
            # Crew
            crew_output = "# Crew Team: Generated Crew\n\n## Agents\n\n"
            for a in agents_data:
                if not a['name']: continue
                crew_output += f"### {a['name']}\n"
                crew_output += f"- **Role**: {a['role']}\n"
                crew_output += f"- **Goal**: {a['goal']}\n"
                crew_output += f"- **Backstory**: {a['backstory']}\n"
                crew_output += f"- **Model**: {a['model']}\n\n"
            
            crew_output += "## Tasks\n\n"
            for t in tasks_data:
                if not t['name']: continue
                out_part = f" [Output: {t['output_file']}]" if t['output_file'] else ""
                crew_output += f"### {t['name']}{out_part}\n"
                crew_output += f"- **Description**: {t['description']}\n"
                crew_output += f"- **Expected Output**: {t['expected_output']}\n"
                crew_output += f"- **Agent**: {t['agent']}\n\n"
            
            with open(self.crew_file, 'w', encoding='utf-8') as f:
                f.write(crew_output)

            # Task
            with open(self.task_file, 'w', encoding='utf-8') as f:
                f.write("# User Task for Agents\n\n" + user_task_content + "\n")
            
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False

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
        
        self.create_widgets()
        
        # Auto-load logic
        self.auto_load()

    def open_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings (.env)")
        width, height = 550, 450
        
        # Position at top-left of main window
        self.root.update_idletasks()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        
        settings_win.geometry(f"{width}x{height}+{root_x}+{root_y}")
        settings_win.transient(self.root)
        settings_win.grab_set()

        env_file = find_dotenv() or ".env"
        # Always reload with override=True to catch changes made in the file or previous saves
        load_dotenv(env_file, override=True)

        keys = ["OLLAMA_SERVER", "OLLAMA_PORT", "OLLAMA_MODEL", "OPENAI_API_KEY", "OTEL_SDK_DISABLED", "PYTHON_VENV_PATH"]
        entries = {}

        container = ttk.Frame(settings_win, padding=20)
        container.pack(fill="both", expand=True)

        def get_models_from_gui():
            self.fetch_ollama_models(entries["OLLAMA_MODEL"], entries["OLLAMA_SERVER"].get(), entries["OLLAMA_PORT"].get())

        for i, key in enumerate(keys):
            ttk.Label(container, text=f"{key}:").grid(row=i, column=0, sticky="e", pady=5, padx=5)
            # Default for PYTHON_VENV_PATH if missing
            val = os.getenv(key, "")
            if key == "PYTHON_VENV_PATH" and not val:
                val = "./venv" 

            if key == "OLLAMA_MODEL":
                # Special handling for Model - use Combobox and Add Refresh button
                entry = ttk.Combobox(container, width=37)
                entry.set(val)
                entry.grid(row=i, column=1, sticky="ew", pady=5, padx=5)
                
                # Refresh Button
                refresh_btn = ttk.Button(container, text="↻", width=3, command=get_models_from_gui)
                refresh_btn.grid(row=i, column=2, padx=2)
                entries[key] = entry
            else:
                entry = ttk.Entry(container, width=40)
                entry.insert(0, val)
                entry.grid(row=i, column=1, sticky="ew", pady=5, padx=5)
                entries[key] = entry
            
        def save_env():
            try:
                for key, entry in entries.items():
                    val = entry.get().strip()
                    set_key(env_file, key, val)
                messagebox.showinfo("Success", "Settings saved to .env")
                settings_win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save .env: {e}")

        ttk.Button(container, text="Save Settings", command=save_env).grid(row=len(keys), column=0, columnspan=3, pady=20)

    def fetch_ollama_models(self, combobox, server=None, port=None):
        if server is None:
            load_dotenv(override=True)
            server = os.getenv("OLLAMA_SERVER", "localhost")
        if port is None:
            port = os.getenv("OLLAMA_PORT", "11434")

        url = f"http://{server}:{port}/api/tags"
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                ollama_models = [m['name'] for m in data.get('models', [])]
                self.ollama_models = ollama_models
                
                self.update_all_model_dropdowns()
                
                # If specific combobox was passed (like from Settings), ensure it's updated too
                if combobox:
                    combobox['values'] = self.ollama_models

                if ollama_models:
                    messagebox.showinfo("Success", f"Found {len(ollama_models)} Ollama models.")
                else:
                    messagebox.showwarning("Warning", "No models found in Ollama response.")
            else:
                messagebox.showerror("Error", f"Server returned status {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to Ollama: {e}")

    def update_all_model_dropdowns(self):
        for a in self.agent_widgets:
            current_val = a['model'].get()
            # Combine fetched models with the current model to ensure it stays visible
            all_vals = list(self.ollama_models)
            if current_val and current_val not in all_vals:
                all_vals.insert(0, current_val)
            a['model']['values'] = all_vals

    def refresh_data(self):
        # Clears current UI and reloads from disk
        for widget in self.agent_widgets:
            widget['frame'].destroy()
        self.agent_widgets.clear()
        
        for widget in self.task_widgets:
            widget['frame'].destroy()
        self.task_widgets.clear()
        
        self.auto_load()
        messagebox.showinfo("Refreshed", "Data reloaded from disk.")

    def get_python_exe(self):
        load_dotenv()
        venv_path = os.getenv("PYTHON_VENV_PATH", "./venv")
        python_exe = "python" # Default fallback
        
        if os.path.exists(venv_path):
             # Try Windows path
             win_py = os.path.join(venv_path, "Scripts", "python.exe")
             # Try Unix path
             unix_py = os.path.join(venv_path, "bin", "python")
             
             if os.path.exists(win_py):
                 python_exe = win_py
             elif os.path.exists(unix_py):
                 python_exe = unix_py
        return python_exe

    def execute_run_crew(self):
        run_win = tk.Toplevel(self.root)
        run_win.title("Running Crew...")
        run_win.geometry("800x600")
        
        # Center
        self.root.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        run_win.geometry(f"+{rx+50}+{ry+50}")
        
        run_win.transient(self.root)
        
        # UI
        ttk.Label(run_win, text="Crew Execution Log:", style="Header.TLabel").pack(anchor="w", padx=10, pady=10)
        
        log_frame = ttk.Frame(run_win)
        log_frame.pack(fill="both", expand=True, padx=10)
        
        log_text = tk.Text(log_frame, font=("Consolas", 9), wrap="word", bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(log_frame, command=log_text.yview)
        log_text.configure(yscrollcommand=scrollbar.set)
        
        log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        progress_frame = ttk.Frame(run_win)
        progress_frame.pack(fill="x", padx=10, pady=10)
        progress = ttk.Progressbar(progress_frame, mode="indeterminate")
        progress.pack(fill="x")
        progress.start(10)
        
        status_lbl = ttk.Label(progress_frame, text="Running...", font=("Segoe UI", 9, "italic"))
        status_lbl.pack(anchor="w", pady=2)
        
        close_btn = ttk.Button(run_win, text="Close", command=run_win.destroy, state="disabled")
        close_btn.pack(pady=10)

        def run_process():
            try:
                python_exe = self.get_python_exe()
                # Unbuffer output for real-time streaming
                cmd = [python_exe, "-u", "script/run_crew.py"]
                
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    encoding='utf-8',
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        run_win.after(0, lambda l=line: update_log(l))
                
                rc = process.poll()
                run_win.after(0, lambda: on_complete(rc))
                
            except Exception as e:
                run_win.after(0, lambda: on_error(str(e)))
        
        def update_log(line):
            log_text.insert(tk.END, line)
            log_text.see(tk.END)
            
        def on_complete(rc):
            progress.stop()
            progress.pack_forget()
            close_btn.configure(state="normal")
            if rc == 0:
                status_lbl.config(text="Execution Finished Successfully", foreground="green")
            else:
                status_lbl.config(text=f"Execution Failed (Code {rc})", foreground="red")
        
        def on_error(msg):
            progress.stop()
            progress.pack_forget()
            close_btn.configure(state="normal")
            log_text.insert(tk.END, f"\nCRITICAL ERROR: {msg}\n")
            status_lbl.config(text="Error to start process", foreground="red")

        threading.Thread(target=run_process, daemon=True).start()

    def open_generate_dialog(self):
        gen_win = tk.Toplevel(self.root)
        gen_win.title("Generate Crew")
        gen_win.geometry("800x850")
        
        # Position centered on main window
        self.root.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        gx = rx + (rw // 2) - 400
        gy = ry + (rh // 2) - 425
        gen_win.geometry(f"+{gx}+{gy}")
        
        gen_win.transient(self.root)
        gen_win.grab_set()

        # First field: Describe task for Crew
        ttk.Label(gen_win, text="Describe task for the Crew:", style="Header.TLabel").pack(anchor="w", padx=20, pady=(20, 10))
        
        task_frame = ttk.Frame(gen_win)
        task_frame.pack(fill="x", padx=20, pady=5)
        task_text = tk.Text(task_frame, height=5, font=("Segoe UI", 10), wrap="word")
        scrollbar = ttk.Scrollbar(task_frame, orient="vertical", command=task_text.yview)
        task_text.configure(yscrollcommand=scrollbar.set)
        task_text.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.add_context_menu(task_text)

        # Second field: Feedback
        ttk.Label(gen_win, text="Feedback:", style="Header.TLabel").pack(anchor="w", padx=20, pady=(15, 10))
        
        feedback_frame = ttk.Frame(gen_win)
        feedback_frame.pack(fill="x", padx=20, pady=5)
        feedback_text = tk.Text(feedback_frame, height=5, font=("Segoe UI", 10), wrap="word")
        feedback_scrollbar = ttk.Scrollbar(feedback_frame, orient="vertical", command=feedback_text.yview)
        feedback_text.configure(yscrollcommand=feedback_scrollbar.set)
        feedback_text.pack(side="left", fill="x", expand=True)
        feedback_scrollbar.pack(side="right", fill="y")
        self.add_context_menu(feedback_text)

        # Model Selection
        model_select_frame = ttk.Frame(gen_win)
        model_select_frame.pack(fill="x", padx=20, pady=10)
        ttk.Label(model_select_frame, text="Generation Model:", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        
        # Current default from .env
        def_model = os.getenv("OLLAMA_MODEL", "")
        model_name_var = tk.StringVar(value=def_model)
        
        # Use existing ollama_models list
        model_combo = ttk.Combobox(model_select_frame, textvariable=model_name_var, values=self.ollama_models, width=40)
        model_combo.pack(side="left", fill="x", expand=True)
        
        refresh_btn = ttk.Button(model_select_frame, text="↻", width=3, 
                               command=lambda e=model_combo: self.fetch_ollama_models(e))
        refresh_btn.pack(side="left", padx=(5, 0))
        
        # Log Output
        ttk.Label(gen_win, text="Generation Log:", style="Header.TLabel").pack(anchor="w", padx=20, pady=(10, 5))
        log_frame = ttk.Frame(gen_win)
        log_frame.pack(fill="both", expand=True, padx=20)
        log_text = tk.Text(log_frame, font=("Consolas", 9), wrap="word", bg="#f0f0f0")
        log_scroll = ttk.Scrollbar(log_frame, command=log_text.yview)
        log_text.configure(yscrollcommand=log_scroll.set)
        log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        # Progress UI
        progress_frame = ttk.Frame(gen_win)
        progress_frame.pack(fill="x", padx=20, pady=10)
        progress = ttk.Progressbar(progress_frame, mode="indeterminate")
        status_lbl = ttk.Label(progress_frame, text="Ready", font=("Segoe UI", 9, "italic"))
        status_lbl.pack(anchor="w")
        
        btn_frame = ttk.Frame(gen_win)
        btn_frame.pack(fill="x", padx=20, pady=20)

        def run_generation():
            description = task_text.get("1.0", tk.END).strip()
            sel_model = model_name_var.get().strip()
            
            if not description:
                messagebox.showwarning("Warning", "Please enter a task description.")
                return

            # Disable UI
            gen_btn.configure(state="disabled")
            refine_btn.configure(state="disabled")
            task_text.configure(state="disabled")
            feedback_text.configure(state="disabled")
            progress.pack(fill="x", pady=5)
            progress.start(10)
            status_lbl.config(text="Generating Crew... This may take a while.")
            log_text.delete("1.0", tk.END)

            def update_log(line):
                log_text.insert(tk.END, line)
                log_text.see(tk.END)

            def thread_target():
                try:
                    python_exe = self.get_python_exe()
                    # Generate WITHOUT context (from scratch)
                    cmd = [python_exe, "-u", "script/create_crew.py", description]
                    if sel_model:
                        cmd.append(sel_model)
                    
                    process = subprocess.Popen(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT, 
                        text=True, 
                        encoding='utf-8',
                        bufsize=1,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    
                    while True:
                        line = process.stdout.readline()
                        if not line and process.poll() is not None:
                            break
                        if line:
                            gen_win.after(0, lambda l=line: update_log(l))
                    
                    rc = process.poll()
                    gen_win.after(0, lambda: on_complete(rc))
                except Exception as e:
                    gen_win.after(0, lambda: on_error(str(e)))

            def on_complete(rc):
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                task_text.configure(state="normal")
                feedback_text.configure(state="normal")
                
                if rc == 0:
                    status_lbl.config(text="Generation Complete!", foreground="green")
                    messagebox.showinfo("Success", "Crew generated successfully!")
                    # Keep window open, just refresh main UI
                    self.refresh_data()
                else:
                    status_lbl.config(text=f"Error Occurred (Code {rc})", foreground="red")
                    messagebox.showerror("Error", "Generation failed. Check the log above.")

            def on_error(err_msg):
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                task_text.configure(state="normal")
                feedback_text.configure(state="normal")
                log_text.insert(tk.END, f"\nCRITICAL ERROR: {err_msg}\n")
                status_lbl.config(text="Execution Error", foreground="red")
                messagebox.showerror("Error", f"Failed to run script: {err_msg}")

            threading.Thread(target=thread_target, daemon=True).start()

        def run_refinement():
            feedback = feedback_text.get("1.0", tk.END).strip()
            sel_model = model_name_var.get().strip()
            
            if not feedback:
                messagebox.showwarning("Warning", "Please enter feedback/refinement instructions.")
                return

            # Check if files exist
            crew_file = "Crew.md"
            task_file = "Task.md"
            
            if not os.path.exists(crew_file) or not os.path.exists(task_file):
                messagebox.showwarning(
                    "Warning", 
                    "Crew.md or Task.md not found. Please generate crew first using Generate button."
                )
                return
            
            # Read existing files for context
            try:
                with open(crew_file, 'r', encoding='utf-8') as f:
                    crew_context = f.read()
                with open(task_file, 'r', encoding='utf-8') as f:
                    task_context = f.read()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read existing files: {e}")
                return

            # Disable UI
            gen_btn.configure(state="disabled")
            refine_btn.configure(state="disabled")
            task_text.configure(state="disabled")
            feedback_text.configure(state="disabled")
            progress.pack(fill="x", pady=5)
            progress.start(10)
            status_lbl.config(text="Refining Crew... This may take a while.")
            log_text.delete("1.0", tk.END)

            def update_log(line):
                log_text.insert(tk.END, line)
                log_text.see(tk.END)

            def thread_target():
                try:
                    python_exe = self.get_python_exe()
                    # Refine WITH context from existing files
                    wrapper_cmd = [
                        python_exe, "-c",
                        f'''
import sys
sys.path.insert(0, "script")
from create_crew import create_crew

create_crew(
    """{feedback.replace('"', '\\"')}""",
    """{sel_model}""" if "{sel_model}" else None,
    """{crew_context.replace('"', '\\"').replace(chr(10), '\\n').replace(chr(13), '')}""",
    """{task_context.replace('"', '\\"').replace(chr(10), '\\n').replace(chr(13), '')}"""
)
'''
                    ]
                    
                    process = subprocess.Popen(
                        wrapper_cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT, 
                        text=True, 
                        encoding='utf-8',
                        bufsize=1,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                        cwd=os.getcwd()
                    )
                    
                    while True:
                        line = process.stdout.readline()
                        if not line and process.poll() is not None:
                            break
                        if line:
                            gen_win.after(0, lambda l=line: update_log(l))
                    
                    rc = process.poll()
                    gen_win.after(0, lambda: on_complete(rc))
                except Exception as e:
                    gen_win.after(0, lambda: on_error(str(e)))

            def on_complete(rc):
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                task_text.configure(state="normal")
                feedback_text.configure(state="normal")
                
                if rc == 0:
                    status_lbl.config(text="Refinement Complete!", foreground="green")
                    messagebox.showinfo("Success", "Crew refined successfully!")
                    # Keep window open, just refresh main UI
                    self.refresh_data()
                else:
                    status_lbl.config(text=f"Error Occurred (Code {rc})", foreground="red")
                    messagebox.showerror("Error", "Refinement failed. Check the log above.")

            def on_error(err_msg):
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                task_text.configure(state="normal")
                feedback_text.configure(state="normal")
                log_text.insert(tk.END, f"\nCRITICAL ERROR: {err_msg}\n")
                status_lbl.config(text="Execution Error", foreground="red")
                messagebox.showerror("Error", f"Failed to run refinement: {err_msg}")

            threading.Thread(target=thread_target, daemon=True).start()

        gen_btn = ttk.Button(btn_frame, text="Generate", command=run_generation)
        gen_btn.pack(side="right", padx=5)
        refine_btn = ttk.Button(btn_frame, text="Refine", command=run_refinement)
        refine_btn.pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=gen_win.destroy).pack(side="right", padx=5)

    def create_widgets(self):
        # Main Layout
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True)

        # Toolbar at top (fixed)
        toolbar = ttk.Frame(self.main_container, padding=10)
        toolbar.pack(side="top", fill="x")
        
        # Toolbar buttons
        ttk.Button(toolbar, text="Refresh", command=self.refresh_data).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Save All", command=self.save_all).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Generate", command=self.open_generate_dialog).pack(side="left", padx=5)
        
        self.settings_btn = ttk.Button(toolbar, text="Settings", command=self.open_settings)
        self.settings_btn.pack(side="left", padx=5)

        # Run Crew Button (Right Aligned)
        ttk.Button(toolbar, text="▶ Run Crew", command=self.execute_run_crew).pack(side="right", padx=5)

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

        # User Task Section
        ttk.Label(self.scrollable_content, text="User Task (Task.md)", style="Header.TLabel").pack(anchor="w", pady=(20, 10))
        self.user_task_text_frame = ttk.Frame(self.scrollable_content)
        self.user_task_text_frame.pack(fill="x", pady=(0, 30))
        
        self.user_task_text = tk.Text(self.user_task_text_frame, height=12, font=("Consolas", 11), padx=10, pady=10, undo=True)
        self.user_task_scrollbar = ttk.Scrollbar(self.user_task_text_frame, orient="vertical", command=self.user_task_text.yview)
        self.user_task_text.configure(yscrollcommand=self.user_task_scrollbar.set)
        
        self.user_task_text.pack(side="left", fill="x", expand=True)
        self.user_task_scrollbar.pack(side="right", fill="y")
        self.add_context_menu(self.user_task_text)

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

    # --- Interaction Helpers ---
    def add_context_menu(self, widget):
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

    def create_scrolled_text(self, parent, height, **kwargs):
        frame = ttk.Frame(parent)
        text = tk.Text(frame, height=height, font=("Segoe UI", 10), undo=True, padx=5, pady=5, **kwargs)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.add_context_menu(text)
        return frame, text

    # --- Row Management ---
    def auto_load(self):
        self.model.load_data()
        
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
        task_content = self.model.load_task()
        self.user_task_text.delete("1.0", tk.END)
        self.user_task_text.insert("1.0", task_content)
        
        self.update_agent_dropdowns()

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
        self.add_context_menu(name_entry)

        # Role
        ttk.Label(frame, text="Role:").grid(row=1, column=0, sticky="e", padx=(5, 10), pady=1)
        role_entry = ttk.Entry(frame)
        role_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=1)
        if data: role_entry.insert(0, data['role'])
        self.add_context_menu(role_entry)

        # Goal
        ttk.Label(frame, text="Goal:").grid(row=2, column=0, sticky="e", padx=(5, 10), pady=1)
        goal_entry = ttk.Entry(frame)
        goal_entry.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=1)
        if data: goal_entry.insert(0, data['goal'])
        self.add_context_menu(goal_entry)

        # Backstory
        ttk.Label(frame, text="Backstory:").grid(row=3, column=0, sticky="ne", padx=(5, 10), pady=10)
        backstory_frame, backstory_text = self.create_scrolled_text(frame, height=4)
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
            # Default to first model if new agent and models are loaded
            model_entry.set(self.ollama_models[0])
            
        refresh_btn = ttk.Button(model_frame, text="↻", width=3, 
                               command=lambda e=model_entry: self.fetch_ollama_models(e))
        refresh_btn.pack(side="right", padx=(5, 0))
        self.add_context_menu(model_entry)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, sticky="e", pady=2)
        
        agent_item = {
            'frame': frame,
            'name_var': name_var,
            'role': role_entry,
            'goal': goal_entry,
            'backstory': backstory_text,
            'model': model_entry
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
        self.add_context_menu(name_entry)

        ttk.Label(frame, text="Output File:").grid(row=0, column=2, sticky="e", padx=(10, 5), pady=1)
        output_entry = ttk.Entry(frame)
        output_entry.grid(row=0, column=3, sticky="ew", padx=(0, 10), pady=1)
        if data: output_entry.insert(0, data['output_file'])
        self.add_context_menu(output_entry)

        ttk.Label(frame, text="Description:").grid(row=1, column=0, sticky="ne", padx=(5, 10), pady=10)
        desc_frame, desc_text = self.create_scrolled_text(frame, height=3)
        desc_frame.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(0, 10), pady=10)
        if data: desc_text.insert("1.0", data['description'])

        ttk.Label(frame, text="Expected Output:").grid(row=2, column=0, sticky="e", padx=(5, 10), pady=1)
        expected_entry = ttk.Entry(frame)
        expected_entry.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(0, 10), pady=1)
        if data: expected_entry.insert(0, data['expected_output'])
        self.add_context_menu(expected_entry)

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
                'model': a['model'].get().strip()
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
        
        success = self.model.save_data(agents_data, tasks_data, user_task_content)
        if success:
            messagebox.showinfo("Success", "Saved Crew.md and Task.md successfully!")
        else:
            messagebox.showerror("Error", "Failed to save files. Check console for details.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CrewAIGUI(root)
    root.mainloop()
