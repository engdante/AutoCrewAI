"""
Tools Registry for CrewAI Tool Agent
Contains essential tools for file operations, web search, and project navigation.
"""

import os
from typing import Type, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from crewai_tools import FileReadTool, DirectoryReadTool
from langchain_community.tools import BraveSearch

class BraveSearchInput(BaseModel):
    """Input schema for BraveSearchTool."""
    query: str = Field(..., description="The search query to look up on the internet.")

class BraveSearchTool(BaseTool):
    name: str = "brave_search"
    description: str = (
        "Search the internet using Brave Search API. "
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

class FileIntelligenceInput(BaseModel):
    """Input schema for FileIntelligenceTool."""
    query: str = Field(..., description="A query string describing what you are looking for in the project (e.g., 'find all Python files', 'locate configuration files').")

class FileIntelligenceTool(BaseTool):
    name: str = "file_intelligence"
    description: str = (
        "Advanced file navigation and content analysis. "
        "Can list relevant files, find specific file types, and summarize project structure. "
        "Input: a query string describing what you are looking for in the project."
    )
    args_schema: Type[BaseModel] = FileIntelligenceInput

    def _run(self, query: str) -> str:
        """Find relevant files based on query."""
        found_files = []
        # Get dynamic output dir from environment or default to local 'output'
        current_output_dir = os.environ.get("CREW_OUTPUT_DIR", "output")
        output_name = os.path.basename(current_output_dir)
        
        exclude_dirs = ["conda", "__pycache__", ".git", ".venv", output_name, "node_modules", "output"]
        
        for root, dirs, files in os.walk(os.getcwd()):
            # Filter directories in-place to prevent walking into excluded ones
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                # Check if file matches common development file types
                if any(ext in file for ext in [".py", ".md", ".env", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini"]):
                    found_files.append(os.path.relpath(os.path.join(root, file)))
        
        # Limit results to prevent overwhelming responses
        limited_results = found_files[:20]
        return f"Found {len(limited_results)} relevant files based on query '{query}':\n" + "\n".join(limited_results)

class FileWriteInput(BaseModel):
    """Input schema for FileWriteTool."""
    filename: str = Field(..., description="The name of the file to write (e.g., 'main.py', 'config.json').")
    content: str = Field(..., description="The content to write to the file.")

class FileWriteTool(BaseTool):
    name: str = "file_writer"
    description: str = (
        "Write content to a file in the output directory. "
        "Use this to save Python scripts, configuration files, or other text documents. "
        "Returns a confirmation message with the file path."
    )
    args_schema: Type[BaseModel] = FileWriteInput

    def _run(self, filename: str, content: str) -> str:
        try:
            # Use dynamic output directory from environment or default to local "output"
            output_dir = os.environ.get("CREW_OUTPUT_DIR")
            if not output_dir:
                output_dir = os.path.join(os.getcwd(), "output")
            
            os.makedirs(output_dir, exist_ok=True)
            
            filepath = os.path.join(output_dir, filename)
            
            # Write content to file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            return f"Successfully wrote to {filepath}"
        except Exception as e:
            return f"Error writing to file {filename}: {str(e)}"

def get_tool_agent_tools():
    """
    Returns a list of tools for the Tool Agent.
    These tools provide comprehensive file operations, web search, and project navigation capabilities.
    """
    tools = []
    
    # Brave Search Tool - for web searches (requires BRAVE_API_KEY in .env)
    brave_key = os.getenv("BRAVE_API_KEY")
    if brave_key and brave_key.strip() and brave_key != "NA":
        tools.append(BraveSearchTool(api_key=brave_key))
    else:
        print("Warning: BRAVE_API_KEY not found or invalid in .env file. BraveSearchTool will not be available.")
    
    # File operations tools
    tools.append(FileReadTool())
    tools.append(FileWriteTool())
    
    # Directory navigation tool
    tools.append(DirectoryReadTool())
    
    # Advanced file intelligence tool
    tools.append(FileIntelligenceTool())
    
    return tools

def get_available_tools():
    """
    Returns information about available tools.
    Useful for debugging and understanding what tools are loaded.
    """
    tools = get_tool_agent_tools()
    
    tool_info = {
        "total_tools": len(tools),
        "available_tools": []
    }
    
    for tool in tools:
        tool_info["available_tools"].append({
            "name": tool.name,
            "description": tool.description
        })
    
    # Check for missing requirements
    missing_brave_key = not os.getenv("BRAVE_API_KEY") or os.getenv("BRAVE_API_KEY") in ["", "NA"]
    
    if missing_brave_key:
        tool_info["missing_requirements"] = {
            "BRAVE_API_KEY": "Set BRAVE_API_KEY in .env file to enable web search"
        }
    else:
        tool_info["missing_requirements"] = {}
    
    return tool_info

if __name__ == "__main__":
    # Test the tools registry
    print("=== Tools Registry Test ===\n")
    
    info = get_available_tools()
    print(f"Total tools available: {info['total_tools']}")
    
    print("\nAvailable tools:")
    for tool in info['available_tools']:
        print(f"  - {tool['name']}: {tool['description']}")
    
    if info['missing_requirements']:
        print("\nMissing requirements:")
        for req, msg in info['missing_requirements'].items():
            print(f"  - {req}: {msg}")
    
    print("\nTo get tools for Tool Agent:")
    print("from tools_registry import get_tool_agent_tools")
    print("tools = get_tool_agent_tools()")