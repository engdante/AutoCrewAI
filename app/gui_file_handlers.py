import os
import shutil
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinterdnd2 import DND_FILES

def copy_files_to_input(self, file_paths):
    """Copy files to the crew's input directory"""
    input_dir = os.path.join(self.model.current_crew_path, "input")
    
    # Ensure input directory exists
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
    
    copied_count = 0
    failed_files = []
    
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
                failed_files.append((filename, str(e)))
                messagebox.showerror("Error", f"Failed to copy {filename}: {e}")
    
    # Show summary message
    if copied_count > 0:
        message = f"Successfully copied {copied_count} file(s)"
        if failed_files:
            message += f"\n\nFailed to copy {len(failed_files)} file(s):"
            for filename, error in failed_files:
                message += f"\n- {filename}: {error}"
        messagebox.showinfo("File Copy Summary", message)
    elif file_paths:
        messagebox.showwarning("Warning", "No files were copied. Please check the console for details.")
    
    # Refresh the file list
    self.refresh_input_files()

def add_input_files(self):
    """Open file dialog to select files to add to input directory"""
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
    failed_files = []
    
    for filename in files_to_remove:
        file_path = os.path.join(input_dir, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                removed_count += 1
            else:
                failed_files.append(filename)
        except Exception as e:
            failed_files.append((filename, str(e)))
    
    # Show summary message
    if removed_count > 0:
        message = f"Successfully removed {removed_count} file(s)"
        if failed_files:
            message += f"\n\nFailed to remove {len(failed_files)} item(s):"
            for item in failed_files:
                if isinstance(item, tuple):
                    message += f"\n- {item[0]}: {item[1]}"
                else:
                    message += f"\n- {item} (not found)"
        messagebox.showinfo("File Removal Summary", message)
    else:
        messagebox.showinfo("Info", "No files were removed.")
    
    # Refresh the file list
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
            
            self.files_listbox.insert(tk.END, filename)
    
    except Exception as e:
        messagebox.showerror("Error", f"Failed to list files: {e}")

def open_input_file(self):
    """Open the selected input file"""
    selection = self.files_listbox.curselection()
    if not selection:
        return
        
    file_name = self.files_listbox.get(selection[0])
    file_path = os.path.join(self.model.current_crew_path, "input", file_name)
    
    if os.path.exists(file_path):
        try:
            if os.name == 'nt':
                os.startfile(file_path)
            elif os.name == 'posix':
                import subprocess
                subprocess.Popen(['xdg-open', file_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")
