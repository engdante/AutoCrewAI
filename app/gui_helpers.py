import os
import subprocess
import requests
import threading
from tkinter import messagebox, ttk
import tkinter as tk
from dotenv import load_dotenv, find_dotenv # Import dotenv

def get_python_exe():
    """Get the python executable path from environment or use default"""
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
    """Execute the run_crew.py script"""
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
    ttk.Label(run_win, text="Crew Execution Log:", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=10)
    
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
            # Load environment variables for the subprocess
            load_dotenv(find_dotenv())
            
            python_exe = get_python_exe()
            
            # Arguments for run_crew.py
            cmd = [
                python_exe, 
                "-u", 
                "script/run_crew.py", 
                "--crew-file", self.model.crew_file,
                "--task-file", self.model.task_file,
                "--output-dir", os.path.join(self.model.current_crew_path, "output"),
                "--crew-name", self.model.current_crew_name # Pass crew_name
            ]
            
            # Determine browser mode (from settings or default)
            browser_mode = self.model.browser_mode # Assuming model has a browser_mode attribute
            if not browser_mode:
                browser_mode = "headless" # Default if not set in model
            cmd.extend(["--browser-mode", browser_mode])

            if self.debug_var.get():
                cmd.append("--debug")
            
            # Pass environment variables to the subprocess
            # This ensures OLLAMA_API_BASE and OLLAMA_MODEL are available to run_crew.py
            env = os.environ.copy()
            
            # Explicitly set OLLAMA_API_BASE if not already set or derived from .env
            ollama_server = env.get("OLLAMA_SERVER")
            ollama_port = env.get("OLLAMA_PORT")
            if ollama_server and ollama_port and not env.get("OLLAMA_API_BASE"):
                env["OLLAMA_API_BASE"] = f"http://{ollama_server}:{ollama_port}"
            
            # Explicitly set OLLAMA_MODEL if not already set
            if not env.get("OLLAMA_MODEL") and self.model.ollama_model: # Assuming model has selected ollama_model
                env["OLLAMA_MODEL"] = self.model.ollama_model


            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                encoding='utf-8',
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                env=env # Pass the modified environment
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

def fetch_ollama_models(self, combobox=None, server=None, port=None):
    """Fetch available models from Ollama server"""
    # Ensure .env is loaded for this context too, if not already
    load_dotenv(find_dotenv())
    if server is None:
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
    """Update all model dropdowns with available models"""
    for a in self.agent_widgets:
        current_val = a['model'].get()
        all_vals = list(self.ollama_models)
        if current_val and current_val not in all_vals:
            all_vals.insert(0, current_val)
        a['model']['values'] = all_vals

def refresh_data(self):
    """Clears current UI and reloads from disk"""
    for widget in self.agent_widgets:
        widget['frame'].destroy()
    self.agent_widgets.clear()
    
    for widget in self.task_widgets:
        widget['frame'].destroy()
    self.task_widgets.clear()
    
    self.auto_load()

_cached_tools_info = None

def get_tools_info():
    """Fetch available tools from the registry and cache them."""
    global _cached_tools_info
    if _cached_tools_info is not None:
        return _cached_tools_info
        
    try:
        # Load environment variables for tool initialization
        load_dotenv(find_dotenv()) 
        
        # Suppress the Pydantic warning if possible
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, message=".*Valid config keys have changed in V2.*")
            
            # Explicitly add root to path if not there
            import sys
            root_path = os.getcwd()
            if root_path not in sys.path:
                sys.path.insert(0, root_path)
                
            from script.tools_registry import get_available_tools
            _cached_tools_info = get_available_tools()
            return _cached_tools_info
    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR fetching tools: {e}")
        traceback.print_exc()
        return {"total_tools": 0, "available_tools": []}
