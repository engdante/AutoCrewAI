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
        self.crews_dir = "crews"
        self.current_crew_name = "default"
        self.current_crew_path = os.path.join(self.crews_dir, "default")
        self.crew_file = os.path.join(self.current_crew_path, "Crew.md")
        self.task_file = os.path.join(self.current_crew_path, "Task.md")
        
        # Ensure crews dir exists
        if not os.path.exists(self.crews_dir):
            os.makedirs(self.crews_dir)

    def get_crews(self):
        crews = []
        if os.path.exists(self.crews_dir):
            for item in os.listdir(self.crews_dir):
                path = os.path.join(self.crews_dir, item)
                if os.path.isdir(path):
                    crews.append(item)
        return sorted(crews)

    def set_active_crew(self, crew_name):
        self.current_crew_name = crew_name
        self.current_crew_path = os.path.join(self.crews_dir, crew_name)
        self.crew_file = os.path.join(self.current_crew_path, "Crew.md")
        self.task_file = os.path.join(self.current_crew_path, "Task.md")
        # Ensure input folder exists for older crews
        input_dir = os.path.join(self.current_crew_path, "input")
        if not os.path.exists(input_dir):
            try:
                os.makedirs(input_dir)
            except: pass
        self.load_data()

    def create_new_crew(self, name, description):
        folder_name = "".join(x for x in name if x.isalnum() or x in "._- ")
        folder_path = os.path.join(self.crews_dir, folder_name)
        
        if os.path.exists(folder_path):
            return False, "Crew already exists"
            
        try:
            os.makedirs(folder_path)
            os.makedirs(os.path.join(folder_path, "output"))
            os.makedirs(os.path.join(folder_path, "input"))
            
            # Create json info
            import json
            info = {
                "name": name,
                "description": description,
                "folder": folder_name
            }
            with open(os.path.join(folder_path, "crew.json"), 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=4)
                
            # Create empty placeholder files
            with open(os.path.join(folder_path, "Crew.md"), 'w', encoding='utf-8') as f:
                f.write(f"# Crew Team: {name}\n\n## Agents\n\n## Tasks\n")
            
            with open(os.path.join(folder_path, "Task.md"), 'w', encoding='utf-8') as f:
                f.write(f"# User Task for Agents\n\n{description}\n")

            return True, folder_name
        except Exception as e:
            return False, str(e)

    def rename_crew(self, current_name, new_name):
        # 1. Check if new name is valid and available
        new_folder_name = "".join(x for x in new_name if x.isalnum() or x in "._- ")
        if not new_folder_name:
            return False, "Invalid name"
            
        current_path = os.path.join(self.crews_dir, current_name)
        new_path = os.path.join(self.crews_dir, new_folder_name)
        
        if os.path.exists(new_path):
             return False, "Crew name/folder already exists"
        
        try:
            # 2. Rename directory
            os.rename(current_path, new_path)
            
            # 3. Update crew.json
            json_path = os.path.join(new_path, "crew.json")
            if os.path.exists(json_path):
                import json
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                data['name'] = new_name
                data['folder'] = new_folder_name
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
            
            # 4. Update internal state if this was active
            if self.current_crew_name == current_name:
                self.set_active_crew(new_folder_name)
                
            return True, new_folder_name
        except Exception as e:
            return False, str(e)

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
            crew_output = f"# Crew Team: {self.current_crew_name}\n\n## Agents\n\n"
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
                cmd = [
                    python_exe, 
                    "-u", 
                    "script/run_crew.py", 
                    "--crew-file", self.model.crew_file,
                    "--task-file", self.model.task_file,
                    "--output-dir", os.path.join(self.model.current_crew_path, "output")
                ]
                
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

        # --- Layout Frames ---
        # Pack bottom frames first so they stay visible
        btn_frame = ttk.Frame(gen_win)
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=20)

        progress_frame = ttk.Frame(gen_win)
        progress_frame.pack(side="bottom", fill="x", padx=20, pady=10)

        # --- Configuration Frame ---
        config_frame = ttk.LabelFrame(gen_win, text="Generation Settings", style="Section.TLabelframe")
        config_frame.pack(side="top", fill="x", padx=20, pady=10)
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)

        # Task Description (Main Task)
        ttk.Label(config_frame, text="Describe task for the Crew:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        task_text_frame = ttk.Frame(config_frame)
        task_text_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=5, pady=2)
        task_text = tk.Text(task_text_frame, height=3, font=("Segoe UI", 10), wrap="word")
        task_scrollbar = ttk.Scrollbar(task_text_frame, orient="vertical", command=task_text.yview)
        task_text.configure(yscrollcommand=task_scrollbar.set)
        task_text.pack(side="left", fill="both", expand=True)
        task_scrollbar.pack(side="right", fill="y")
        self.add_context_menu(task_text)

        # Architecture Selection
        ttk.Label(config_frame, text="Architecture:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        arch_var = tk.StringVar(value="sequential")
        arch_combo = ttk.Combobox(config_frame, textvariable=arch_var, values=["sequential", "hierarchical"], state="readonly", width=15)
        arch_combo.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        arch_combo.current(0) # Force select "sequential"

        # Supervisor Checkbox - Using IntVar for more reliable state
        supervisor_enabled = tk.IntVar(value=0)
        supervisor_check = ttk.Checkbutton(config_frame, text="Enable Supervisor", variable=supervisor_enabled)
        supervisor_check.grid(row=2, column=2, sticky="w", padx=(20, 5), pady=5)

        # Tool Agent Checkbox - Using IntVar for more reliable state
        tool_agent_enabled = tk.IntVar(value=0)
        tool_agent_check = ttk.Checkbutton(config_frame, text="Enable Tool Agent", variable=tool_agent_enabled)
        tool_agent_check.grid(row=2, column=3, sticky="w", padx=(5, 5), pady=5)

        # Model Selection for general agents
        ttk.Label(config_frame, text="Default Model:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        def_model = os.getenv("OLLAMA_MODEL", "")
        model_name_var = tk.StringVar(value=def_model)
        model_combo = ttk.Combobox(config_frame, textvariable=model_name_var, values=self.ollama_models, width=20)
        model_combo.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        # Supervisor Model Selection
        ttk.Label(config_frame, text="Supervisor Model:").grid(row=3, column=2, sticky="w", padx=(20, 5), pady=5)
        sup_model_var = tk.StringVar(value=def_model)
        sup_model_combo = ttk.Combobox(config_frame, textvariable=sup_model_var, values=self.ollama_models, width=20)
        sup_model_combo.grid(row=3, column=3, sticky="ew", padx=5, pady=5)

        # Refresh Button for Models - Aligned with Default Model field
        def update_both_combos():
            self.fetch_ollama_models(model_combo)
            sup_model_combo['values'] = self.ollama_models # Sync values

        refresh_btn = ttk.Button(config_frame, text="↻ Models", width=10,
                               command=update_both_combos)
        refresh_btn.grid(row=4, column=1, sticky="w", padx=5, pady=5)

        # Feedback/Refinement Field
        ttk.Label(gen_win, text="Feedback / Refinement (for Refine button):", style="Header.TLabel").pack(side="top", anchor="w", padx=20, pady=(10, 5))
        feedback_frame = ttk.Frame(gen_win)
        feedback_frame.pack(side="top", fill="x", padx=20, pady=5)
        feedback_text = tk.Text(feedback_frame, height=3, font=("Segoe UI", 10), wrap="word")
        feedback_scrollbar = ttk.Scrollbar(feedback_frame, orient="vertical", command=feedback_text.yview)
        feedback_text.configure(yscrollcommand=feedback_scrollbar.set)
        feedback_text.pack(side="left", fill="x", expand=True)
        feedback_scrollbar.pack(side="right", fill="y")
        self.add_context_menu(feedback_text)

        # Log Output (Expands to fill remaining space)
        ttk.Label(gen_win, text="Generation Log:", style="Header.TLabel").pack(side="top", anchor="w", padx=20, pady=(10, 5))
        log_frame = ttk.Frame(gen_win)
        log_frame.pack(side="top", fill="both", expand=True, padx=20)
        log_text = tk.Text(log_frame, font=("Consolas", 9), wrap="word", bg="#f0f0f0")
        log_scroll = ttk.Scrollbar(log_frame, command=log_text.yview)
        log_text.configure(yscrollcommand=log_scroll.set)
        log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        # Progress UI (in bottom frame)
        progress = ttk.Progressbar(progress_frame, mode="indeterminate")
        status_lbl = ttk.Label(progress_frame, text="Ready", font=("Segoe UI", 9, "italic"))
        status_lbl.pack(anchor="w")

        # Define functions BEFORE creating buttons
        def run_generation():
            description = task_text.get("1.0", tk.END).strip()
            sel_model = model_name_var.get().strip()
            selected_arch = arch_var.get()
            sup_enabled = supervisor_enabled.get()
            sup_model = sup_model_var.get().strip()
            tool_agent_enabled_flag = tool_agent_enabled.get()

            if not description:
                messagebox.showwarning("Warning", "Please enter a task description.")
                return

            # Disable UI
            gen_btn.configure(state="disabled")
            refine_btn.configure(state="disabled")
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
                    cmd = [python_exe, "-u", "script/create_crew.py", description]
                    if sel_model: cmd.extend(["--model", sel_model])
                    cmd.extend(["--architecture", selected_arch])
                    cmd.extend(["--output-dir", self.model.current_crew_path])
                    if sup_enabled:
                        cmd.append("--supervisor")
                        if sup_model: cmd.extend(["--supervisor-model", sup_model])
                    if tool_agent_enabled_flag: cmd.append("--tool-agent")

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
                if rc == 0:
                    status_lbl.config(text="Generation Complete!", foreground="green")
                    messagebox.showinfo("Success", "Crew generated successfully!")
                    self.refresh_data()
                else:
                    status_lbl.config(text=f"Error Occurred (Code {rc})", foreground="red")

            def on_error(msg):
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                log_text.insert(tk.END, f"\nCRITICAL ERROR: {msg}\n")

            threading.Thread(target=thread_target, daemon=True).start()

        def run_refinement():
            feedback = feedback_text.get("1.0", tk.END).strip()
            sel_model = model_name_var.get().strip()
            selected_arch = arch_var.get()
            sup_enabled = supervisor_enabled.get()
            sup_model = sup_model_var.get().strip()
            tool_agent_enabled_flag = tool_agent_enabled.get()

            if not feedback:
                messagebox.showwarning("Warning", "Please enter feedback/refinement instructions.")
                return

            crew_file = self.model.crew_file
            task_file = self.model.task_file
            if not os.path.exists(crew_file) or not os.path.exists(task_file):
                messagebox.showwarning("Warning", "Crew.md or Task.md not found.")
                return

            try:
                with open(crew_file, 'r', encoding='utf-8') as f: crew_context = f.read()
                with open(task_file, 'r', encoding='utf-8') as f: task_context = f.read()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read existing files: {e}")
                return

            gen_btn.configure(state="disabled")
            refine_btn.configure(state="disabled")
            progress.pack(fill="x", pady=5)
            progress.start(10)
            status_lbl.config(text="Refining Crew... This may take a while.")
            log_text.delete("1.0", tk.END)

            def thread_target():
                try:
                    python_exe = self.get_python_exe()
                    def esc(s): return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

                    script_code = f'''
import sys
sys.path.insert(0, "script")
from create_crew import create_crew
create_crew(
    task_description="{esc(feedback)}",
    model_name="{esc(sel_model)}" if "{sel_model}" else None,
    crew_context="{esc(crew_context)}",
    task_context="{esc(task_context)}",
    architecture="{selected_arch}",
    enable_supervisor={sup_enabled},
    enable_tool_agent={tool_agent_enabled_flag},
    supervisor_model="{esc(sup_model)}" if "{sup_model}" else None,
    output_dir=r"{self.model.current_crew_path}"
)
'''

                    process = subprocess.Popen(
                        [python_exe, "-c", script_code],
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

            def update_log(line):
                log_text.insert(tk.END, line)
                log_text.see(tk.END)

            def on_complete(rc):
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                if rc == 0:
                    status_lbl.config(text="Refinement Complete!", foreground="green")
                    messagebox.showinfo("Success", "Crew refined successfully!")
                    self.refresh_data()
                else:
                    status_lbl.config(text=f"Error Occurred (Code {rc})", foreground="red")

            def on_error(msg):
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                log_text.insert(tk.END, f"\nCRITICAL ERROR: {msg}\n")

            threading.Thread(target=thread_target, daemon=True).start()

        # Create Buttons (in bottom frame) - NOW it's safe to use run_generation/refinement
        gen_btn = ttk.Button(btn_frame, text="Generate Crew", command=run_generation)
        gen_btn.pack(side="left", padx=(0, 10), expand=True, fill="x")
        
        refine_btn = ttk.Button(btn_frame, text="Refine Crew", command=run_refinement)
        refine_btn.pack(side="left", padx=(0, 10), expand=True, fill="x")
        
        close_btn = ttk.Button(btn_frame, text="Close", command=gen_win.destroy)
        close_btn.pack(side="right")

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

        # Input Files Section
        ttk.Label(self.scrollable_content, text="Input Files", style="Header.TLabel").pack(anchor="w", pady=(20, 10))
        
        # Drop zone frame
        self.drop_zone_frame = ttk.LabelFrame(self.scrollable_content, text="Drag & Drop Files Here", style="Section.TLabelframe")
        self.drop_zone_frame.pack(fill="x", pady=(0, 10))
        
        # Drop zone label
        self.drop_zone_label = ttk.Label(
            self.drop_zone_frame, 
            text="📁 Drag files here or click 'Add Files' button\nFiles will be copied to the crew's input/ directory",
            font=("Segoe UI", 10),
            foreground="gray",
            justify="center"
        )
        self.drop_zone_label.pack(pady=30, padx=20)
        
        # Buttons for file management
        files_btn_frame = ttk.Frame(self.scrollable_content)
        files_btn_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(files_btn_frame, text="+ Add Files", command=self.add_input_files).pack(side="left", padx=(0, 5))
        ttk.Button(files_btn_frame, text="🗑 Remove Selected", command=self.remove_input_files).pack(side="left", padx=5)
        ttk.Button(files_btn_frame, text="📂 Open Folder", command=self.open_input_folder).pack(side="left", padx=5)
        ttk.Button(files_btn_frame, text="🔄 Refresh", command=self.refresh_input_files).pack(side="left", padx=5)
        
        # File list
        self.files_list_frame = ttk.Frame(self.scrollable_content)
        self.files_list_frame.pack(fill="x", pady=(0, 10))
        
        # Listbox with scrollbar
        files_scroll_frame = ttk.Frame(self.files_list_frame)
        files_scroll_frame.pack(fill="x")
        
        self.files_listbox = tk.Listbox(
            files_scroll_frame, 
            height=6, 
            font=("Consolas", 10),
            selectmode=tk.EXTENDED
        )
        files_scrollbar = ttk.Scrollbar(files_scroll_frame, orient="vertical", command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=files_scrollbar.set)
        
        self.files_listbox.pack(side="left", fill="x", expand=True)
        files_scrollbar.pack(side="right", fill="y")
        
        # Enable drag and drop
        self.setup_drag_drop()

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
        # Load Crews
        crews = self.model.get_crews()
        self.crew_combo['values'] = crews
        if self.model.current_crew_name in crews:
            self.crew_combo.set(self.model.current_crew_name)
        elif crews:
            self.crew_combo.current(0)
            self.change_crew(None) # Trigger load

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
        user_task = self.model.load_task()
        self.user_task_text.delete("1.0", tk.END)
        self.user_task_text.insert("1.0", user_task)
        
        self.update_agent_dropdowns()
        
        # Refresh input files list
        self.refresh_input_files()

    def change_crew(self, event):
        new_crew = self.crew_combo.get()
        if new_crew and new_crew != self.model.current_crew_name:
            self.model.set_active_crew(new_crew)
            self.refresh_data()

    def open_new_crew_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Crew")
        dialog.geometry("400x250")
        
        self.root.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        dialog.geometry(f"+{rx+100}+{ry+100}")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Crew Name (Folder Name):").pack(anchor="w", padx=20, pady=(20, 5))
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(padx=20, pady=5)
        
        ttk.Label(dialog, text="Description:").pack(anchor="w", padx=20, pady=(10, 5))
        desc_entry = ttk.Entry(dialog, width=40)
        desc_entry.pack(padx=20, pady=5)
        
        def create():
            name = name_entry.get().strip()
            desc = desc_entry.get().strip()
            if not name:
                messagebox.showwarning("Required", "Please enter a name.")
                return
            
            success, msg = self.model.create_new_crew(name, desc)
            if success:
                self.auto_load() # Refresh list
                self.crew_combo.set(msg)
                self.change_crew(None)
                dialog.destroy()
                messagebox.showinfo("Success", f"Crew '{msg}' created!")
            else:
                messagebox.showerror("Error", f"Failed to create crew: {msg}")
        
        ttk.Button(dialog, text="Create", command=create).pack(pady=20)

    def open_rename_crew_dialog(self):
        current_crew = self.model.current_crew_name
        if not current_crew: return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Rename Crew: {current_crew}")
        dialog.geometry("400x150")
        
        self.root.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        dialog.geometry(f"+{rx+100}+{ry+100}")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="New Crew Name:").pack(anchor="w", padx=20, pady=(20, 5))
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.insert(0, current_crew)
        name_entry.pack(padx=20, pady=5)
        
        def do_rename():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showwarning("Required", "Please enter a name.")
                return
            
            if new_name == current_crew:
                dialog.destroy()
                return

            success, msg = self.model.rename_crew(current_crew, new_name)
            if success:
                self.auto_load() # Refresh list and reload if active
                # Select the renamed crew
                self.crew_combo.set(msg) 
                
                dialog.destroy()
                messagebox.showinfo("Success", f"Renamed to '{msg}'!")
            else:
                messagebox.showerror("Error", f"Failed to rename: {msg}")
        
        ttk.Button(dialog, text="Rename", command=do_rename).pack(pady=10)

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

    # --- Input Files Management ---
    
    def setup_drag_drop(self):
        """Setup drag and drop functionality for the drop zone"""
        # Try to enable drag & drop with tkinterdnd2
        try:
            from tkinterdnd2 import DND_FILES
            
            # Register drop zone for file drops
            self.drop_zone_frame.drop_target_register(DND_FILES)
            self.drop_zone_frame.dnd_bind('<<Drop>>', self.on_drop)
            self.drop_zone_frame.dnd_bind('<<DragEnter>>', self.on_drop_enter)
            self.drop_zone_frame.dnd_bind('<<DragLeave>>', self.on_drop_leave)
            
            # Update label to show drag & drop is enabled
            self.drop_zone_label.configure(
                text="📁 Drag files here or click 'Add Files' button\n✅ Drag & Drop enabled\nFiles will be copied to the crew's input/ directory"
            )
            print("✅ Drag & Drop enabled (tkinterdnd2 loaded successfully)")
            
        except ImportError:
            # tkinterdnd2 not installed
            self.drop_zone_label.configure(
                text="📁 Click 'Add Files' button to add files\n⚠️ Drag & Drop disabled (tkinterdnd2 not installed)\nCommand: pip install tkinterdnd2",
                foreground="orange"
            )
            print("⚠️ Drag & Drop disabled. Install tkinterdnd2: pip install tkinterdnd2")
            
        except Exception as e:
            # tkinterdnd2 installed but failed to initialize (common issue)
            self.drop_zone_label.configure(
                text="📁 Click 'Add Files' button to add files\n⚠️ Drag & Drop unavailable (tkinterdnd2 initialization failed)\nNote: This is a known issue with some tkinter versions\nManual file selection works perfectly!",
                foreground="orange"
            )
            print(f"⚠️ Drag & Drop initialization failed: {e}")
            print("   Note: This is a known compatibility issue with tkinterdnd2")
            print("   Manual file selection via 'Add Files' button works perfectly!")
    
    def on_drop_enter(self, event):
        """Visual feedback when dragging over drop zone"""
        self.drop_zone_label.configure(foreground="blue")
        return event.action
    
    def on_drop_leave(self, event):
        """Reset visual feedback when leaving drop zone"""
        self.drop_zone_label.configure(foreground="gray")
        return event.action
    
    def on_drop(self, event):
        """Handle file drop event"""
        try:
            files = self.root.tk.splitlist(event.data)
            self.copy_files_to_input(files)
            self.drop_zone_label.configure(foreground="gray")
        except Exception as e:
            messagebox.showerror("Drop Error", f"Failed to process dropped files: {e}")
    
    def add_input_files(self):
        """Open file dialog to select files to add to input directory"""
        from tkinter import filedialog
        
        files = filedialog.askopenfilenames(
            title="Select Files to Add to Input Directory",
            filetypes=[
                ("All Files", "*.*"),
                ("Text Files", "*.txt"),
                ("Markdown Files", "*.md"),
                ("JSON Files", "*.json"),
                ("CSV Files", "*.csv"),
                ("Python Files", "*.py")
            ]
        )
        
        if files:
            self.copy_files_to_input(files)
    
    def copy_files_to_input(self, file_paths):
        """Copy files to the crew's input directory"""
        import shutil
        
        input_dir = os.path.join(self.model.current_crew_path, "input")
        
        # Ensure input directory exists
        if not os.path.exists(input_dir):
            os.makedirs(input_dir)
        
        copied_count = 0
        for file_path in file_paths:
            if os.path.isfile(file_path):
                try:
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(input_dir, filename)
                    
                    # Check if file already exists
                    if os.path.exists(dest_path):
                        response = messagebox.askyesno(
                            "File Exists", 
                            f"File '{filename}' already exists. Overwrite?"
                        )
                        if not response:
                            continue
                    
                    shutil.copy2(file_path, dest_path)
                    copied_count += 1
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to copy {filename}: {e}")
        
        if copied_count > 0:
            messagebox.showinfo("Success", f"Copied {copied_count} file(s) to input directory")
            self.refresh_input_files()
    
    def remove_input_files(self):
        """Remove selected files from input directory"""
        selected_indices = self.files_listbox.curselection()
        
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select files to remove")
            return
        
        files_to_remove = [self.files_listbox.get(i) for i in selected_indices]
        
        response = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete {len(files_to_remove)} file(s)?"
        )
        
        if not response:
            return
        
        input_dir = os.path.join(self.model.current_crew_path, "input")
        removed_count = 0
        
        for filename in files_to_remove:
            file_path = os.path.join(input_dir, filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    removed_count += 1
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete {filename}: {e}")
        
        if removed_count > 0:
            messagebox.showinfo("Success", f"Removed {removed_count} file(s)")
            self.refresh_input_files()
    
    def open_input_folder(self):
        """Open the input folder in file explorer"""
        input_dir = os.path.join(self.model.current_crew_path, "input")
        
        # Ensure directory exists
        if not os.path.exists(input_dir):
            os.makedirs(input_dir)
        
        # Open folder in file explorer
        if os.name == 'nt':  # Windows
            os.startfile(input_dir)
        elif os.name == 'posix':  # Linux/Mac
            import subprocess
            subprocess.Popen(['xdg-open', input_dir])
    
    def refresh_input_files(self):
        """Refresh the list of files in the input directory"""
        input_dir = os.path.join(self.model.current_crew_path, "input")
        
        # Clear current list
        self.files_listbox.delete(0, tk.END)
        
        # Check if directory exists
        if not os.path.exists(input_dir):
            os.makedirs(input_dir)
            return
        
        # List all files
        try:
            files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
            files.sort()
            
            for filename in files:
                file_path = os.path.join(input_dir, filename)
                file_size = os.path.getsize(file_path)
                
                # Format size
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                display_text = f"{filename} ({size_str})"
                self.files_listbox.insert(tk.END, filename)
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list files: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = CrewAIGUI(root)
    root.mainloop()