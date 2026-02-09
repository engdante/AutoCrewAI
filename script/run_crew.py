import re
import os
import sys
import warnings
import logging
import traceback

# Suppress Pydantic V2 compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pydantic')

# Suppress CrewAI Tracing/Telemetry messages
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["LITELLM_LOGGING"] = "false"

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv

# Import tools registry
from tools_registry import get_tool_agent_tools

# Path configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
INPUT_DIR = os.path.join(PROJECT_ROOT, "input")
# Default to None, will be set relative to crew file if not provided
OUTPUT_DIR = None 

def setup_logging(output_dir):
    """Sets up logging to a run_debug.log file in the crew's root directory."""
    if not output_dir:
        return
        
    # Move up one level from output directory to reach crew root
    crew_root = os.path.dirname(output_dir)
    log_file = os.path.join(crew_root, "run_debug.log")
    
    # Reset existing handlers to avoid duplicates
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)
            
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        encoding='utf-8',
        force=True
    )
    logging.info("--- Execution Started ---")
    print(f"--- [DEBUG] Logging details to: {log_file} ---")

env_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(env_path)

# Get configuration from environment variables
OLLAMA_SERVER = os.getenv("OLLAMA_SERVER", "localhost")
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Derived URL
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or f"http://{OLLAMA_SERVER}:{OLLAMA_PORT}"
os.environ["OLLAMA_API_BASE"] = OLLAMA_BASE_URL

# Initialize LLM with Ollama configuration
ollama_llm = LLM(
    model=f"ollama/{OLLAMA_MODEL}",
    base_url=OLLAMA_BASE_URL,
    timeout=300,        # Increase timeout to 5 minutes
    max_retries=3       # Retry 3 times on connection errors
)

def parse_crew_md(file_path, task_input_content):
    def parse_markdown_fields(markdown_block, is_config=False):
        parsed_data = {}
        
        # Enhanced regex patterns for better flexibility
        if is_config:
            # Pattern for config fields: "- Key: value" or "- **Key**: value"
            field_patterns = [
                r"^\s*-\s*\*\*(?P<key>[^:]+?)\*\*\s*:(?P<value>.*?)(?=\n\s*-\s*(?:\*\*[^:]+?\*\*|[^:]+?):|\n\s*##[^#]|\Z)",
                r"^\s*-\s*(?P<key>[^:]+?)\s*:(?P<value>.*?)(?=\n\s*-\s*[^:]+?:|\n\s*##[^#]|\Z)"
            ]
        else:
            # Pattern for agents/tasks: "- **Key**: value" (most common)
            field_patterns = [
                r"^\s*-\s*\*\*(?P<key>[^:]+?)\*\*\s*:(?P<value>.*?)(?=\n\s*-\s*\*\*[^:]+?\*\*\s*:|\n\s*###|\Z)",
                # Fallback for simpler format
                r"^\s*-\s*(?P<key>[^:]+?)\s*:(?P<value>.*?)(?=\n\s*-\s*[^:]+?:|\n\s*###|\Z)"
            ]
        
        # Try each pattern until we find matches
        for pattern in field_patterns:
            for match in re.finditer(pattern, markdown_block, re.DOTALL | re.IGNORECASE | re.MULTILINE):
                key = match.group("key").strip()
                value = match.group("value").strip()
                parsed_data[key] = value
            if parsed_data:  # If we found matches with this pattern, stop
                break
                
        return parsed_data
    
    def validate_crew_structure(content):
        """Validate Crew.md structure and return detailed error messages"""
        errors = []
        
        # Check for required sections
        if not re.search(r'^# Crew Team:', content, re.MULTILINE):
            errors.append("Missing or malformed crew title (expected: '# Crew Team: [Name]')")
        
        config_section = re.search(r'## Configuration(.*?)(## Agents|$)', content, re.DOTALL)
        if not config_section:
            errors.append("Missing '## Configuration' section")
        else:
            config_fields = parse_markdown_fields(config_section.group(1), is_config=True)
            if "Architecture" not in config_fields:
                errors.append("Missing 'Architecture' in Configuration section")
        
        agents_section = re.search(r'## Agents(.*?)(## Tasks|$)', content, re.DOTALL)
        if not agents_section:
            errors.append("Missing '## Agents' section")
        else:
            agent_blocks = re.findall(r'### (.*?)\n(.*?)(?=### |$)', agents_section.group(1), re.DOTALL)
            if not agent_blocks:
                errors.append("No agents found in '## Agents' section")
        
        tasks_section = re.search(r'## Tasks(.*)', content, re.DOTALL)
        if not tasks_section:
            errors.append("Missing '## Tasks' section")
        else:
            task_blocks = re.findall(r'### (.*?)\n(.*?)(?=### |$)', tasks_section.group(1), re.DOTALL)
            if not task_blocks:
                errors.append("No tasks found in '## Tasks' section")
        
        return errors

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Validate Crew.md structure before parsing
        validation_errors = validate_crew_structure(content)
        if validation_errors:
            error_msg = "Crew.md validation failed:\n" + "\n".join(f"  - {error}" for error in validation_errors)
            print(error_msg)
            logging.error(f"Crew.md validation failed: {validation_errors}")
            return None, {}, [], "sequential", None

        # Parse Crew Title
        title_match = re.search(r'^# Crew Team: (.*)', content, re.MULTILINE)
        crew_title = title_match.group(1).strip() if title_match else "Unnamed Crew"

        # Initialize configuration defaults
        crew_architecture = "sequential"
        crew_supervisor_agent_name = None

        # Parse Configuration section
        config_section_match = re.search(r'## Configuration(.*?)(## Agents|$)', content, re.DOTALL)
        if config_section_match:
            config_content = config_section_match.group(1)
            config_fields = parse_markdown_fields(config_content, is_config=True)
            crew_architecture = config_fields.get("Architecture", "sequential").lower()
            crew_supervisor_agent_name = config_fields.get("Supervisor Agent")
            if crew_supervisor_agent_name and crew_supervisor_agent_name.lower() == 'none':
                crew_supervisor_agent_name = None
        
        # Split into Agents and Tasks sections
        agents_section = re.search(r'## Agents(.*?)(## Tasks|$)', content, re.DOTALL)
        tasks_section = re.search(r'## Tasks(.*)', content, re.DOTALL)

        agents = {}
        if agents_section:
            agent_blocks = re.findall(r'### (.*?)\n(.*?)(?=### |$)', agents_section.group(1), re.DOTALL)
            for name, details in agent_blocks:
                name = name.strip()
                agent_fields = parse_markdown_fields(details)
                
                # Determine which LLM to use
                custom_model_name = agent_fields.get("Model")
                if custom_model_name:
                    # Standardize model name - ensure it has ollama/ prefix if missing
                    if not custom_model_name.startswith("ollama/"):
                        custom_model_name = f"ollama/{custom_model_name}"
                    
                    agent_llm = LLM(
                        model=custom_model_name,
                        base_url=OLLAMA_BASE_URL,
                        timeout=300,
                        max_retries=3
                    )
                    print(f"Agent {name} using custom model: {custom_model_name}")
                else:
                    agent_llm = ollama_llm # Default from config
                
                # Check if this agent has tools (Tool Agent)
                tools_string = agent_fields.get("Tools", "")
                agent_tools = []
                
                if tools_string:
                    # Load tools from tools registry
                    available_tools = get_tool_agent_tools()
                    tool_names = [t.strip() for t in tools_string.split(',')]
                    
                    for tool in available_tools:
                        if tool.name in tool_names:
                            agent_tools.append(tool)
                            print(f"  ✅ Loaded tool '{tool.name}' for agent '{name}'")
                        else:
                            print(f"  ⚠️ Tool '{tool.name}' not in requested tools list")
                    
                    if not agent_tools:
                        print(f"  ⚠️ No tools loaded for agent '{name}' - requested tools not available")
                else:
                    print(f"  ℹ️ No tools specified for agent '{name}'")
                
                agents[name] = Agent(
                    role=agent_fields.get("Role", ""),
                    goal=agent_fields.get("Goal", ""),
                    backstory=agent_fields.get("Backstory", ""),
                    llm=agent_llm,
                    tools=agent_tools,  # Add tools here
                    verbose=True,
                    allow_delegation=False
                )

        tasks_data = []
        if tasks_section:
            task_blocks = re.findall(r'### (.*?)\n(.*?)(?=### |$)', tasks_section.group(1), re.DOTALL)
            for task_header, details in task_blocks:
                task_header = task_header.strip()
                # Extract custom output file if specified in [Output: filename.md]
                output_file_match = re.search(r'\[Output:\s*(.*?)\]', task_header)
                custom_output_file = output_file_match.group(1).strip() if output_file_match else None
                # Clean task name for internal logic
                task_name = re.sub(r'\[Output:.*?\]', '', task_header).strip()

                task_fields = parse_markdown_fields(details)
                
                agent_name_for_task = task_fields.get("Agent")
                agent_inst = agents.get(agent_name_for_task) if agent_name_for_task else None
                
                if agent_inst:
                    desc_text = task_fields.get("Description", "")
                    
                    # Injection 1: {task_input} from Task.md
                    if "{task_input}" in desc_text:
                        desc_text = desc_text.replace("{task_input}", task_input_content)
                    elif task_input_content:
                        # Only prepend if no explicit placeholder AND Task.md is not empty
                        desc_text = f"Context from Task.md:\n{task_input_content}\n\nTask Description: {desc_text}"

                    # Injection 2: Dynamic [[filename]] support
                    file_placeholders = re.findall(r'\[\[(.*?)\]\]', desc_text)
                    crew_dir = os.path.dirname(os.path.abspath(file_path))
                    crew_input_dir = os.path.join(crew_dir, "input")
                    
                    for f_name in file_placeholders:
                        f_name = f_name.strip()
                        # Look in 3 places: 
                        # 1. Crew's input/ folder
                        # 2. Global input/ folder
                        # 3. Project root
                        crew_specific_path = os.path.join(crew_input_dir, f_name)
                        # If f_name starts with 'input/', also try without 'input/' prefix for crew folder
                        if f_name.startswith("input/") or f_name.startswith("input\\"):
                            f_name_short = f_name[6:]
                            crew_specific_path_alt = os.path.join(crew_input_dir, f_name_short)
                        else:
                            crew_specific_path_alt = None

                        input_path = os.path.join(INPUT_DIR, f_name)
                        root_path = os.path.join(PROJECT_ROOT, f_name)
                        
                        file_path_resolved = None
                        if os.path.exists(crew_specific_path):
                            file_path_resolved = crew_specific_path
                        elif crew_specific_path_alt and os.path.exists(crew_specific_path_alt):
                            file_path_resolved = crew_specific_path_alt
                        elif os.path.exists(input_path):
                            file_path_resolved = input_path
                        elif os.path.exists(root_path):
                            file_path_resolved = root_path
                        
                        if file_path_resolved:
                            with open(file_path_resolved, 'r', encoding='utf-8') as f:
                                f_content = f.read()
                            
                            # Apply sampling if the file is large
                            if len(f_content) > 50000:
                                print(f"Sampling large file: {f_name}")
                                chunk = 15000
                                f_content = (
                                    f"[WARNING: Content of {f_name} has been sampled due to its large size ({len(f_content)} chars). "
                                    f"Significant portions of the document have been omitted. "
                                    f"If the analysis requires specific sections not shown below, please request them individually.]\n\n"
                                    f"--- START OF FILE ---\n{f_content[:chunk]}\n\n"
                                    f"--- MIDDLE OF FILE ---\n{f_content[len(f_content)//2 - chunk//2 : len(f_content)//2 + chunk//2]}\n\n"
                                    f"--- END OF FILE ---\n{f_content[-chunk:]}"
                                )
                            
                            desc_text = desc_text.replace(f"[[{f_name}]]", f_content)
                            print(f"Injected content from {file_path_resolved}")
                        else:
                            print(f"Warning: File [[{f_name}]] not found in crew input/, global input/ or project root.")

                    tasks_data.append({
                        "name": task_name,
                        "custom_output": custom_output_file,
                        "task": Task(
                            description=desc_text,
                            expected_output=task_fields.get("Expected Output", ""),
                            agent=agent_inst
                        )
                    })

        return crew_title, agents, tasks_data, crew_architecture, crew_supervisor_agent_name

    except FileNotFoundError:
        print(f"Error: Crew.md file not found at {file_path}")
        logging.error(f"Crew.md file not found: {file_path}")
        return None, {}, [], "sequential", None
    except Exception as e:
        print(f"Error parsing Crew.md: {str(e)}")
        logging.error(f"Error parsing Crew.md: {str(e)}", exc_info=True)
        return None, {}, [], "sequential", None

def run_crew(crew_file, task_file, output_dir=None, enable_web_search=False, debug=False):
    global OUTPUT_DIR
    
    # If output_dir is provided via CLI, use it. 
    # Otherwise, use the 'output' folder inside the crew's directory.
    if output_dir:
        OUTPUT_DIR = output_dir
    else:
        crew_dir = os.path.dirname(os.path.abspath(crew_file))
        OUTPUT_DIR = os.path.join(crew_dir, "output")
        
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.environ["CREW_OUTPUT_DIR"] = OUTPUT_DIR
    if debug:
        setup_logging(OUTPUT_DIR)

    try:
        logging.info(f"Loading crew from: {crew_file}")
        logging.info(f"Loading task from: {task_file}")
        
        print(f"--- Loading Crew from {crew_file} ---")
        
        task_input_content = ""
        if os.path.exists(task_file):
            with open(task_file, 'r', encoding='utf-8') as f:
                task_input_content = f.read()
        
        title, agents_dict, tasks_data, architecture, supervisor_agent_name = parse_crew_md(crew_file, task_input_content)
        
        # Check if parsing failed
        if title is None:
            print("Failed to parse Crew.md. Please check the validation errors above.")
            return
        
        agent_list = list(agents_dict.values())
        
        # Inject Web Search Tools if enabled
        if enable_web_search:
            print(f"--- [INFO] Web Search Enabled: Injecting tools into all agents ---")
            logging.info("Web Search Enabled via CLI flag")
            try:
                extra_tools = get_tool_agent_tools()
                tool_names = [t.name for t in extra_tools]
                print(f"    Tools injected: {', '.join(tool_names)}")
                
                for agent in agent_list:
                    # Add tools if not already present
                    existing_names = [t.name for t in agent.tools] if agent.tools else []
                    new_tools = [t for t in extra_tools if t.name not in existing_names]
                    
                    if new_tools:
                        if agent.tools is None:
                            agent.tools = []
                        agent.tools.extend(new_tools)
                        print(f"    -> Added {len(new_tools)} tools to agent '{agent.role}'")
            except Exception as e:
                logging.error(f"Failed to inject tools: {e}")
                print(f"    [WARNING] Failed to inject tools: {e}")
        
        crew_process = Process.sequential
        manager_agent = None

        if architecture == "hierarchical":
            crew_process = Process.hierarchical
            if supervisor_agent_name:
                # 1. Try to find supervisor by the exact '### Name' from Crew.md (using agents_dict)
                manager_agent = agents_dict.get(supervisor_agent_name)
                
                # 2. Try to find by role name if direct match fails
                if not manager_agent:
                    for agent in agent_list:
                        if agent.role == supervisor_agent_name:
                            manager_agent = agent
                            break

                # 3. Fallback: try to find an agent whose name contains "supervisor" or "manager"
                if not manager_agent:
                    for agent_name, agent_obj in agents_dict.items():
                        if "supervisor" in agent_name.lower() or "manager" in agent_name.lower():
                            manager_agent = agent_obj
                            print(f"Warning: Exact supervisor agent '{supervisor_agent_name}' not found. Using '{agent_name}' as fallback manager agent.")
                            logging.warning(f"Fallback supervisor used: {agent_name}")
                            break

                if not manager_agent:
                    msg = f"Hierarchical architecture specified, but supervisor agent '{supervisor_agent_name}' not found."
                    print(f"Error: {msg}")
                    logging.error(msg)
                    return

        # 1. Logic: Skip Style Analysis if book_summary.md already exists in output
        book_summary_path = os.path.join(OUTPUT_DIR, "book_summary.md")
        if os.path.exists(book_summary_path):
            print(f"--- [DEBUG] book_summary.md found in output/. Checking tasks to skip... ---")
            filtered_tasks = []
            summary_to_inject = None
            
            # Read existing summary once
            with open(book_summary_path, "r", encoding="utf-8") as f:
                summary_to_inject = f.read()

            for td in tasks_data:
                if td["custom_output"] == "book_summary.md":
                    print(f"--- [SKIP] Skipping task '{td['name']}' because output already exists. ---")
                else:
                    # If we are skipping the style task, inject its content into the development task
                    if any(k in td["name"].lower() for k in ["enrich", "develop", "write"]):
                        print(f"--- [INJECT] Injecting existing book_summary.md into '{td['name']}' ---")
                        td["task"].description = f"Existing Style Guide (from book_summary.md):\n{summary_to_inject}\n\n{td['task'].description}"
                    filtered_tasks.append(td)
            
            tasks_data = filtered_tasks

        # 2. Logic: Inject Task_Feedback.md if it exists in output
        feedback_path = os.path.join(OUTPUT_DIR, "Task_Feedback.md")
        if os.path.exists(feedback_path):
            print(f"--- [FEEDBACK] Task_Feedback.md found in output/. Injecting into Enrichment task... ---")
            with open(feedback_path, "r", encoding='utf-8') as f:
                feedback_content = f.read()
            
            for td in tasks_data:
                # Inject into the Enrichment/Development task
                if any(k in td["name"].lower() for k in ["enrich", "develop", "write"]):
                    print(f"--- [INJECT] Injecting feedback into '{td['name']}' ---")
                    td["task"].description = f"PREVIOUS EDITORIAL FEEDBACK TO ADDRESS:\n{feedback_content}\n\n{td['task'].description}"
                    # We only inject into the first matching task (the main production one)
                    break

        if not agent_list or not tasks_data:
            print("Error: No agents or tasks found. Check your Crew.md syntax.")
            logging.error("No agents or tasks parsed.")
            return

        print(f"Starting Crew: {title} (Architecture: {architecture.upper()})")
        if manager_agent:
            print(f"    Manager Agent: {manager_agent.role}")
        
        crew = Crew(
            agents=[a for a in agent_list if a != manager_agent] if manager_agent else agent_list,
            tasks=[td["task"] for td in tasks_data],
            process=crew_process,
            manager_agent=manager_agent if manager_agent else None, # Pass manager_agent only if hierarchical
            verbose=True
        )

        logging.info("Kickoff starting...")
        result = crew.kickoff()
        logging.info("Kickoff completed successfully.")
        
        # Process outputs
        for td in tasks_data:
            t_name = td["name"].lower()
            t_output = td["task"].output.raw if hasattr(td["task"].output, 'raw') else str(td["task"].output)
            
            # Priority 1: Custom output file
            if td["custom_output"]:
                target_f = td["custom_output"]
            # Priority 2: Keyword-based routing
            elif any(k in t_name for k in ["plan", "strategy", "analysis", "guide", "outline"]):
                target_f = "Task_Plan.md"
            elif any(k in t_name for k in ["result", "execute", "enrich", "develop", "write", "creation"]):
                target_f = "Task_Result.md"
            elif any(k in t_name for k in ["feedback", "evaluation", "review", "edit"]):
                target_f = "Task_Feedback.md"
            else:
                target_f = None

            if target_f:
                # Write to output directory
                output_path = os.path.join(OUTPUT_DIR, target_f)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(t_output)
                print(f"Saved output of '{td['name']}' to {output_path}")

        print("\n\n########################")
        print(f"## FINAL RESULT FOR {title}:")
        print("########################\n")
        print(result)
        
    except Exception as e:
        logging.critical("CRITICAL ERROR during execution:", exc_info=True)
        print(f"\n❌ FATAL ERROR: {str(e)}")
        print(f"See {os.path.join(OUTPUT_DIR, 'run_debug.log')} for full technical details.")
        raise

if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in environment variables.")
    
    import argparse

    parser = argparse.ArgumentParser(description="Run CrewAI agent team")
    parser.add_argument("--crew-file", help="Path to Crew.md", default=None)
    parser.add_argument("--task-file", help="Path to Task.md", default=None)
    parser.add_argument("--output-dir", help="Directory for output files", default=None)
    
    parser.add_argument("--web-search", action="store_true", help="Enable web search for all agents")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()

    # Look for Crew.md and Task.md in crews/default if not specified
    default_crew_path = os.path.join(PROJECT_ROOT, 'crews', 'default')
    crew_file = args.crew_file if args.crew_file else os.path.join(default_crew_path, 'Crew.md')
    task_file = args.task_file if args.task_file else os.path.join(default_crew_path, 'Task.md')
    
    run_crew(crew_file, task_file, args.output_dir, args.web_search, args.debug)