import os
import subprocess
import sys
from typing import Type, Optional, List
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from crewai_tools import SerperDevTool, FileReadTool, DirectoryReadTool, ScrapeWebsiteTool
from langchain_community.tools import BraveSearch

from langchain_community.tools import BraveSearch

class DependencyManagerInput(BaseModel):
    """Input schema for DependencyManagerTool."""
    package: str = Field(..., description="The name of the Python package to install (e.g., 'pandas').")

class DependencyManagerTool(BaseTool):
    name: str = "dependency_manager"
    description: str = (
        "Install missing Python libraries in the local conda environment. "
        "Use this if you encounter a ModuleNotFoundError or need a specific library. "
        "Returns the status of the installation."
    )
    args_schema: Type[BaseModel] = DependencyManagerInput

    def _get_pip_executable(self):
        """Finds the pip executable in the local conda environment."""
        local_conda = os.path.join(os.getcwd(), "conda")
        if os.path.exists(local_conda):
            if sys.platform == "win32":
                pip_exe = os.path.join(local_conda, "Scripts", "pip.exe")
            else:
                pip_exe = os.path.join(local_conda, "bin", "pip")
            
            if os.path.exists(pip_exe):
                return pip_exe
        return "pip" # Fallback to system pip if conda not found (risky but allows execution)

    def _run(self, package: str) -> str:
        try:
            pip_exe = self._get_pip_executable()
            print(f"Installing package {package} using {pip_exe}...")
            
            result = subprocess.run(
                [pip_exe, "install", package],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return f"Successfully installed {package}."
            else:
                return f"Failed to install {package}.\n--- STDOUT ---\n{result.stdout}\n--- STDERR ---\n{result.stderr}"
        except Exception as e:
            return f"Error installing package: {str(e)}"

class PythonSandboxInput(BaseModel):
    """Input schema for PythonSandboxTool."""
    code: str = Field(..., description="The Python code to execute.")
    filename: Optional[str] = Field(None, description="Optional filename to save the code to before execution.")

class PythonSandboxTool(BaseTool):
    name: str = "python_sandbox"
    description: str = (
        "Run Python code in an isolated subprocess. "
        "Returns the standard output and standard error. "
        "Useful for testing scripts, validating logic, or performing calculations. "
        "Input should be a JSON object with 'code' and optional 'filename'."
    )
    args_schema: Type[BaseModel] = PythonSandboxInput

    def _get_python_executable(self):
        """Finds the python executable in the local conda environment or falls back to sys.executable."""
        local_conda = os.path.join(os.getcwd(), "conda")
        if os.path.exists(local_conda):
            if sys.platform == "win32":
                conda_python = os.path.join(local_conda, "python.exe")
            else:
                conda_python = os.path.join(local_conda, "bin", "python")
            
            if os.path.exists(conda_python):
                return conda_python
        return sys.executable

    def _run(self, code: str, filename: str = "temp_script.py") -> str:
        try:
            # Save the code to a file
            output_dir = os.path.join(os.getcwd(), "output")
            filepath = os.path.join(output_dir, filename)
            os.makedirs(output_dir, exist_ok=True)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Use the local conda python if available
            python_exe = self._get_python_executable()
            
            # Execute the code with UTF-8 encoding forced
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            result = subprocess.run(
                [python_exe, filepath],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            output = f"Executed with: {python_exe}\n"
            output += f"--- STDOUT ---\n{result.stdout}\n"
            if result.stderr:
                output += f"--- STDERR ---\n{result.stderr}\n"
            
            output += f"--- STATUS ---\nExit Code: {result.returncode}"
            return output
            
        except subprocess.TimeoutExpired:
            return "Error: Execution timed out after 30 seconds."
        except Exception as e:
            return f"Error executing code: {str(e)}"

class DocumentationTool(BaseTool):
    name: str = "documentation_tool"
    description: str = (
        "Generate or verify content for README.md and script docstrings. "
        "Ensures project and modules are well-documented according to best practices."
    )

    def _run(self, content: str, target: str = "README.md") -> str:
        try:
            filepath = os.path.join(os.getcwd(), "output", target)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote documentation to {target}"
        except Exception as e:
            return f"Error writing documentation: {str(e)}"

class SafeDirectoryReadTool(DirectoryReadTool):
    """
    A safer version of DirectoryReadTool that automatically ignores 
    large or sensitive directories like conda, .git, and __pycache__.
    """
    def _run(self, **kwargs) -> str:
        # We wrap the output to filter the directory listing
        full_output = super()._run(**kwargs)
        if not full_output:
            return full_output
            
        lines = full_output.split("\n")
        safe_lines = []
        
        # Patterns to exclude
        exclude_patterns = ["conda/", "conda\\", "__pycache__", ".git", ".env", ".venv"]
        
        for line in lines:
            if not any(pattern in line for pattern in exclude_patterns):
                safe_lines.append(line)
        
        status_msg = "\n(Some directories like 'conda' are hidden for performance/safety reasons.)"
        return "\n".join(safe_lines) + status_msg

class FileIntelligenceTool(BaseTool):
    name: str = "file_intelligence"
    description: str = (
        "Advanced file navigation and content analysis. "
        "Can list files, find specific terms, and summarize structures. "
        "Input: a query string describing what you are looking for in the project."
    )

    def _run(self, query: str) -> str:
        # Simple implementation using existing tools logic
        found_files = []
        exclude_dirs = ["conda", "__pycache__", ".git", ".venv", "output"]
        for root, dirs, files in os.walk(os.getcwd()):
            # Filter directories in-place to prevent walking into them
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if any(ext in file for ext in [".py", ".md", ".env", ".txt"]):
                    found_files.append(os.path.relpath(os.path.join(root, file)))
        
        return f"Found relevant files based on query '{query}':\n" + "\n".join(found_files[:20])

class BraveSearchInput(BaseModel):
    """Input schema for BraveSearchTool."""
    query: str = Field(..., description="The search query to look up on the internet.")

class BraveSearchTool(BaseTool):
    name: str = "brave_search"
    description: str = (
        "Search the internet using Brave Search. "
        "Useful for finding technical documentation, latest news, and code examples. "
        "Input should be a search query string."
    )
    args_schema: Type[BaseModel] = BraveSearchInput
    api_key: str = Field(..., exclude=True)

    def _run(self, query: str) -> str:
        try:
            brave = BraveSearch.from_api_key(
                api_key=self.api_key, 
                search_params={"count": 5}
            )
            return brave.run(query)
        except Exception as e:
            return f"Error searching internet: {str(e)}"

class PersistentLoggingInput(BaseModel):
    """Input schema for PersistentLoggingTool."""
    content: str = Field(..., description="The content to append to the log.")
    log_name: str = Field(..., description="The name of the log file (e.g., 'architect_log.md').")

class PersistentLoggingTool(BaseTool):
    name: str = "persistent_logging"
    description: str = (
        "Append information to a specific log file in the output directory. "
        "Use this to persist state, record decisions, or document progress for other agents. "
        "Returns a confirmation message."
    )
    args_schema: Type[BaseModel] = PersistentLoggingInput

    def _run(self, content: str, log_name: str) -> str:
        try:
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, log_name)
            
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(f"\n--- Log Entry ---\n{content}\n")
            
            return f"Successfully appended to {log_name}."
        except Exception as e:
            return f"Error writing to log {log_name}: {str(e)}"

class FileWriteInput(BaseModel):
    """Input schema for FileWriteTool."""
    filename: str = Field(..., description="The name of the file to write (e.g., 'main.py').")
    content: str = Field(..., description="The content to write to the file.")

class FileWriteTool(BaseTool):
    name: str = "file_writer"
    description: str = (
        "Write content to a file in the output directory. "
        "Use this to save Python scripts, configuration files, or other text documents. "
        "Returns a confirmation message."
    )
    args_schema: Type[BaseModel] = FileWriteInput

    def _run(self, filename: str, content: str) -> str:
        try:
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            return f"Successfully wrote to {filename} in the output directory."
        except Exception as e:
            return f"Error writing to file {filename}: {str(e)}"

def get_ralph_tools(mode="all"):
    """
    Returns a list of tools based on mode.
    - "all": Includes file tools, sandbox, documentation, and web tools (if API key available).
    - "web": Focuses on internet search and scraping.
    - "local": Focuses on file manipulation and sandbox execution.
    """
    tools = []
    
    # Core tools that might be useful in both modes (but be careful with file tools in pure web mode)
    if mode == "all" or mode == "local":
        tools.append(FileReadTool())
        tools.append(SafeDirectoryReadTool(directory=os.getcwd()))
        tools.append(PythonSandboxTool())
        tools.append(DependencyManagerTool())
        tools.append(DocumentationTool())
        tools.append(FileIntelligenceTool())
        tools.append(PersistentLoggingTool())
        tools.append(FileWriteTool())
    
    if mode == "web" or mode == "all":
        brave_key = os.getenv("BRAVE_API_KEY")
        if brave_key and brave_key != "NA":
            tools.append(BraveSearchTool(api_key=brave_key))
        
        # Scrape tools for web mode
        tools.append(ScrapeWebsiteTool())
        
    return tools
