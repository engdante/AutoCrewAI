import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import subprocess
import requests
import json
from .gui_models import CrewModel
from .gui_helpers import get_python_exe, fetch_ollama_models, get_tools_info
from .gui_widgets import add_context_menu, ToolSelector

def open_new_crew_dialog(root, app):
    dialog = tk.Toplevel(root)
    dialog.title("Create New Crew")
    dialog.geometry("400x250")
    
    root.update_idletasks()
    rx = root.winfo_x()
    ry = root.winfo_y()
    dialog.geometry(f"+{rx+100}+{ry+100}")
    dialog.transient(root)
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
        
        success, msg = app.model.create_new_crew(name, desc)
        if success:
            app.auto_load()  # Refresh list
            for widget in dialog.winfo_children():
                if isinstance(widget, ttk.Combobox) and widget['values']:
                    if msg in widget['values']:
                        widget.set(msg)
                        break
            dialog.destroy()
            messagebox.showinfo("Success", f"Crew '{msg}' created!")
        else:
            messagebox.showerror("Error", f"Failed to create crew: {msg}")
    
    ttk.Button(dialog, text="Create", command=create).pack(pady=20)

def open_rename_crew_dialog(root, app):
    current_crew = app.model.current_crew_name
    if not current_crew: return

    dialog = tk.Toplevel(root)
    dialog.title(f"Rename Crew: {current_crew}")
    dialog.geometry("400x150")
    
    root.update_idletasks()
    rx = root.winfo_x()
    ry = root.winfo_y()
    dialog.geometry(f"+{rx+100}+{ry+100}")
    dialog.transient(root)
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

        success, msg = app.model.rename_crew(current_crew, new_name)
        if success:
            app.auto_load()  # Refresh list and reload if active
            # Select the renamed crew
            for widget in dialog.winfo_children():
                if isinstance(widget, ttk.Combobox) and widget['values']:
                    if msg in widget['values']:
                        widget.set(msg)
                        break
            
            dialog.destroy()
            messagebox.showinfo("Success", f"Renamed to '{msg}'!")
        else:
            messagebox.showerror("Error", f"Failed to rename: {msg}")
    
    ttk.Button(dialog, text="Rename", command=do_rename).pack(pady=10)

def open_settings(root, app):
    settings_win = tk.Toplevel(root)
    settings_win.title("Settings (.env)")
    width, height = 550, 450
    
    root.update_idletasks()
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    
    settings_win.geometry(f"{width}x{height}+{root_x}+{root_y}")
    settings_win.transient(root)
    settings_win.grab_set()

    from dotenv import load_dotenv, set_key, find_dotenv
    env_file = find_dotenv() or ".env"
    load_dotenv(env_file, override=True)

    keys = ["OLLAMA_SERVER", "OLLAMA_PORT", "OLLAMA_MODEL", "OPENAI_API_KEY", "OTEL_SDK_DISABLED", "PYTHON_VENV_PATH"]
    entries = {}

    container = ttk.Frame(settings_win, padding=20)
    container.pack(fill="both", expand=True)

    def get_models_from_gui():
        fetch_ollama_models(app, entries["OLLAMA_MODEL"], entries["OLLAMA_SERVER"].get(), entries["OLLAMA_PORT"].get())

    for i, key in enumerate(keys):
        ttk.Label(container, text=f"{key}:").grid(row=i, column=0, sticky="e", pady=5, padx=5)
        val = os.getenv(key, "")
        if key == "PYTHON_VENV_PATH" and not val:
            val = "./venv" 

        if key == "OLLAMA_MODEL":
            entry = ttk.Combobox(container, width=37)
            entry.set(val)
            entry.grid(row=i, column=1, sticky="ew", pady=5, padx=5)
            
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

def open_generate_dialog(root, app):
    gen_win = tk.Toplevel(root)
    gen_win.title("Generate Crew")
    gen_win.geometry("800x950")
    
    root.update_idletasks()
    rx = root.winfo_x()
    ry = root.winfo_y()
    rw = root.winfo_width()
    rh = root.winfo_height()
    gx = rx + (rw // 2) - 400
    gy = ry + (rh // 2) - 475
    gen_win.geometry(f"+{gx}+{gy}")
    
    gen_win.transient(root)

    # --- Configuration Frame ---
    config_frame = ttk.LabelFrame(gen_win, text="Generation Settings")
    config_frame.pack(side="top", fill="x", padx=20, pady=10)
    config_frame.columnconfigure(1, weight=1)
    config_frame.columnconfigure(3, weight=1)

    # Task Description
    ttk.Label(config_frame, text="Describe task for the Crew:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    ttk.Label(config_frame, text="Tools").grid(row=0, column=4, sticky="w", padx=5, pady=5)

    task_text_frame = ttk.Frame(config_frame)
    task_text_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=5, pady=2)
    task_text = tk.Text(task_text_frame, height=8, font=("Segoe UI", 10), wrap="word")
    task_scrollbar = ttk.Scrollbar(task_text_frame, orient="vertical", command=task_text.yview)
    task_text.configure(yscrollcommand=task_scrollbar.set)
    task_text.pack(side="left", fill="both", expand=True)
    task_scrollbar.pack(side="right", fill="y")
    add_context_menu(task_text)

    # Tool Selector for Generate Dialog
    tools_info = get_tools_info()
    tool_selector = ToolSelector(config_frame, task_text, tools_info)
    tool_selector.grid(row=1, column=4, sticky="nsew", padx=5, pady=2)
    config_frame.columnconfigure(4, weight=1)

    # Architecture Selection
    ttk.Label(config_frame, text="Architecture:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    arch_var = tk.StringVar(value="sequential")
    arch_combo = ttk.Combobox(config_frame, textvariable=arch_var, values=["sequential", "hierarchical"], state="readonly", width=15)
    arch_combo.grid(row=2, column=1, sticky="w", padx=5, pady=5)
    arch_combo.current(0)

    # Supervisor Checkbox
    supervisor_enabled = tk.IntVar(value=0)
    supervisor_check = ttk.Checkbutton(config_frame, text="Enable Supervisor", variable=supervisor_enabled)
    supervisor_check.grid(row=2, column=2, sticky="w", padx=(20, 5), pady=5)

    # Web Search Checkbox
    web_search_enabled = tk.IntVar(value=0)
    web_search_check = ttk.Checkbutton(config_frame, text="Use Web Search", variable=web_search_enabled)
    web_search_check.grid(row=2, column=3, sticky="w", padx=(5, 5), pady=5)

    # Model Selection
    ttk.Label(config_frame, text="Default Model:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
    def_model = os.getenv("OLLAMA_MODEL", "")
    model_name_var = tk.StringVar(value=def_model)
    model_combo = ttk.Combobox(config_frame, textvariable=model_name_var, values=app.ollama_models, width=20)
    model_combo.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

    # Supervisor Model Selection
    ttk.Label(config_frame, text="Supervisor Model:").grid(row=3, column=2, sticky="w", padx=(20, 5), pady=5)
    sup_model_var = tk.StringVar(value=def_model)
    sup_model_combo = ttk.Combobox(config_frame, textvariable=sup_model_var, values=app.ollama_models, width=20)
    sup_model_combo.grid(row=3, column=3, sticky="ew", padx=5, pady=5)

    # Debug Checkbox
    debug_enabled = tk.IntVar(value=0)
    debug_check = ttk.Checkbutton(config_frame, text="Generate Debug Log", variable=debug_enabled)
    debug_check.grid(row=4, column=0, sticky="w", padx=5, pady=5)

    # Refresh Button
    def update_both_combos():
        fetch_ollama_models(app, model_combo, None, None)
        sup_model_combo['values'] = app.ollama_models

    refresh_btn = ttk.Button(config_frame, text="↻ Models", width=10,
                           command=update_both_combos)
    refresh_btn.grid(row=4, column=1, sticky="w", padx=5, pady=5)

    # Feedback/Refinement Field
    ttk.Label(gen_win, text="Feedback / Refinement (for Refine button):").pack(side="top", anchor="w", padx=20, pady=(10, 5))
    feedback_frame = ttk.Frame(gen_win)
    feedback_frame.pack(side="top", fill="x", padx=20, pady=5)
    feedback_text = tk.Text(feedback_frame, height=4, font=("Segoe UI", 10), wrap="word")
    feedback_scrollbar = ttk.Scrollbar(feedback_frame, orient="vertical", command=feedback_text.yview)
    feedback_text.configure(yscrollcommand=feedback_scrollbar.set)
    feedback_text.pack(side="left", fill="x", expand=True)
    feedback_scrollbar.pack(side="right", fill="y")
    add_context_menu(feedback_text)

    # Log Output
    ttk.Label(gen_win, text="Generation Log:").pack(side="top", anchor="w", padx=20, pady=(10, 5))
    log_frame = ttk.Frame(gen_win)
    log_frame.pack(side="top", fill="both", expand=True, padx=20)
    log_text = tk.Text(log_frame, height=15, font=("Consolas", 9), wrap="word", bg="#f0f0f0")
    log_scroll = ttk.Scrollbar(log_frame, command=log_text.yview)
    log_text.configure(yscrollcommand=log_scroll.set)
    log_text.pack(side="left", fill="both", expand=True)
    log_scroll.pack(side="right", fill="y")
    add_context_menu(log_text)

    # Progress UI
    progress_frame = ttk.Frame(gen_win)
    progress_frame.pack(fill="x", padx=20, pady=10)
    progress = ttk.Progressbar(progress_frame, mode="indeterminate")
    status_lbl = ttk.Label(progress_frame, text="Ready", font=("Segoe UI", 9, "italic"))
    status_lbl.pack(anchor="w")

    # Buttons
    btn_frame = ttk.Frame(gen_win)
    btn_frame.pack(side="bottom", fill="x", padx=20, pady=20)

    gen_crew_file = os.path.join(app.model.current_crew_path, "GenCrew.md")

    def save_gen_crew():
        data = {
            "task_description": task_text.get("1.0", tk.END).strip(),
            "architecture": arch_var.get(),
            "supervisor_enabled": supervisor_enabled.get(),
            "web_search_enabled": web_search_enabled.get(),
            "model": model_name_var.get().strip(),
            "supervisor_model": sup_model_var.get().strip(),
            "debug_enabled": debug_enabled.get(),
            "feedback": feedback_text.get("1.0", tk.END).strip()
        }
        try:
            with open(gen_crew_file, 'w', encoding='utf-8') as f:
                f.write("<!-- GenCrew JSON Data DO NOT EDIT -->\n")
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving GenCrew.md: {e}")

    def load_gen_crew():
        if os.path.exists(gen_crew_file):
            try:
                with open(gen_crew_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if not lines: return
                    # Skip the first comment line
                    json_str = "".join(lines[1:])
                    data = json.loads(json_str)
                    
                if "task_description" in data:
                    task_text.delete("1.0", tk.END)
                    task_text.insert("1.0", data["task_description"])
                if "architecture" in data:
                    arch_var.set(data["architecture"])
                if "supervisor_enabled" in data:
                    supervisor_enabled.set(data["supervisor_enabled"])
                if "web_search_enabled" in data:
                    web_search_enabled.set(data["web_search_enabled"])
                if "model" in data:
                    model_name_var.set(data["model"])
                if "supervisor_model" in data:
                    sup_model_var.set(data["supervisor_model"])
                if "feedback" in data:
                    feedback_text.delete("1.0", tk.END)
                    feedback_text.insert("1.0", data["feedback"])
                if "debug_enabled" in data:
                    debug_enabled.set(data["debug_enabled"])
            except Exception as e:
                print(f"Error loading GenCrew.md: {e}")

    def run_generation():
        description = task_text.get("1.0", tk.END).strip()
        sel_model = model_name_var.get().strip()
        selected_arch = arch_var.get()
        sup_enabled = supervisor_enabled.get()
        sup_model = sup_model_var.get().strip()
        web_search_enabled_flag = web_search_enabled.get()
        debug_flag = debug_enabled.get()

        if not description:
            messagebox.showwarning("Warning", "Please enter a task description.")
            return

        save_gen_crew()

        gen_btn.configure(state="disabled")
        refine_btn.configure(state="disabled")
        progress.pack(fill="x", pady=5)
        progress.start(10)
        status_lbl.config(text="Generating Crew... This may take a while.")
        log_text.delete("1.0", tk.END)

        def update_log(line):
            if not gen_win.winfo_exists(): return
            try:
                log_text.insert(tk.END, line)
                log_text.see(tk.END)
            except tk.TclError:
                pass

        def thread_target():
            try:
                python_exe = get_python_exe()
                cmd = [python_exe, "-u", "script/create_crew.py", description]
                if sel_model: cmd.extend(["--model", sel_model])
                cmd.extend(["--architecture", selected_arch])
                cmd.extend(["--output-dir", app.model.current_crew_path])
                if sup_enabled:
                    cmd.append("--supervisor")
                    if sup_model: cmd.extend(["--supervisor-model", sup_model])
                if web_search_enabled_flag: cmd.append("--web-search")
                if debug_flag: cmd.append("--debug")

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
            if not gen_win.winfo_exists(): return
            try:
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                if rc == 0:
                    status_lbl.config(text="Generation Complete!", foreground="green")
                    messagebox.showinfo("Success", "Crew generated successfully!")
                    app.refresh_data()
                else:
                    status_lbl.config(text=f"Error Occurred (Code {rc})", foreground="red")
            except tk.TclError:
                pass

        def on_error(msg):
            if not gen_win.winfo_exists(): return
            try:
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                log_text.insert(tk.END, f"\nCRITICAL ERROR: {msg}\n")
            except tk.TclError:
                pass

        threading.Thread(target=thread_target, daemon=True).start()

    def run_refinement():
        feedback = feedback_text.get("1.0", tk.END).strip()
        sel_model = model_name_var.get().strip()
        selected_arch = arch_var.get()
        sup_enabled = supervisor_enabled.get()
        sup_model = sup_model_var.get().strip()
        web_search_enabled_flag = web_search_enabled.get()
        debug_flag = debug_enabled.get()

        if not feedback:
            messagebox.showwarning("Warning", "Please enter feedback/refinement instructions.")
            return

        save_gen_crew()

        crew_file = app.model.crew_file
        task_file = app.model.task_file
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
                python_exe = get_python_exe()
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
    enable_web_search={web_search_enabled_flag},
    supervisor_model="{esc(sup_model)}" if "{sup_model}" else None,
    output_dir=r"{app.model.current_crew_path}",
    debug={True if debug_flag else False}
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
            if not gen_win.winfo_exists(): return
            try:
                log_text.insert(tk.END, line)
                log_text.see(tk.END)
            except tk.TclError:
                pass

        def on_complete(rc):
            if not gen_win.winfo_exists(): return
            try:
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                if rc == 0:
                    status_lbl.config(text="Refinement Complete!", foreground="green")
                    messagebox.showinfo("Success", "Crew refined successfully!")
                    app.refresh_data()
                else:
                    status_lbl.config(text=f"Error Occurred (Code {rc})", foreground="red")
            except tk.TclError:
                pass

        def on_error(msg):
            if not gen_win.winfo_exists(): return
            try:
                progress.stop()
                progress.pack_forget()
                gen_btn.configure(state="normal")
                refine_btn.configure(state="normal")
                log_text.insert(tk.END, f"\nCRITICAL ERROR: {msg}\n")
            except tk.TclError:
                pass

        threading.Thread(target=thread_target, daemon=True).start()

    # Create buttons
    gen_btn = ttk.Button(btn_frame, text="Generate Crew", command=run_generation)
    gen_btn.pack(side="left", padx=(0, 10), expand=True, fill="x")
    
    refine_btn = ttk.Button(btn_frame, text="Refine Crew", command=run_refinement)
    refine_btn.pack(side="left", padx=(0, 10), expand=True, fill="x")
    
    close_btn = ttk.Button(btn_frame, text="Close", command=gen_win.destroy)
    close_btn.pack(side="right")

    load_gen_crew()