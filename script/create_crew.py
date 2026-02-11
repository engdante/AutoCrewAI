import logging
import os
import sys
import warnings
import json

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

# Path configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Load environment variables from .env file in project root
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
    base_url=OLLAMA_BASE_URL
)

def setup_logging(output_dir):
    """Sets up logging to a create_debug.log file."""
    if not output_dir:
        output_dir = os.getcwd()
    
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, "create_debug.log")
    
    # Reset existing handlers
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
    logging.info("--- Crew Generation Started ---")
    print(f"--- [DEBUG] Logging details to: {log_file} ---")

def clean_markdown(content):
    """Removes markdown code block formatting if present."""
    if content.startswith("```"):
        # Remove first line
        content = "\n".join(content.split("\n")[1:])
        # Remove last line if it is just backticks
        if content.strip().endswith("```"):
             content = content.replace("```", "").strip() # Aggressive cleanup at end
    return content.strip()

def validate_crew_md(crew_md_content):
    """Validate generated Crew.md against strict schema"""
    errors = []
    warnings = []
    
    # Check structure
    if not crew_md_content.startswith("# Crew Team:"):
        errors.append("Crew.md must start with '# Crew Team: [Name]'")
    
    # Check required sections
    required_sections = ["## Configuration", "## Agents", "## Tasks"]
    for section in required_sections:
        if section not in crew_md_content:
            errors.append(f"Missing required section: {section}")
    
    # Check Configuration section
    config_match = re.search(r'## Configuration(.*?)(## Agents|$)', crew_md_content, re.DOTALL)
    if config_match:
        config_content = config_match.group(1)
        config_fields = re.findall(r'^\s*-\s*(?P<key>[^:]+?)\s*:(?P<value>.*?)(?=\n\s*-\s*[^:]+?:|\n\s*##[^#]|\Z)', config_content, re.MULTILINE)
        config_dict = {k.strip(): v.strip() for k, v in config_fields}
        
        if "Architecture" not in config_dict:
            errors.append("Configuration section must contain 'Architecture' field")
        else:
            valid_architectures = ["sequential", "hierarchical"]
            if config_dict["Architecture"].lower() not in valid_architectures:
                errors.append(f"Architecture must be one of: {', '.join(valid_architectures)}")
        
        if "Supervisor Agent" not in config_dict:
            errors.append("Configuration section must contain 'Supervisor Agent' field")
    
    # Check Agents section
    agents_match = re.search(r'## Agents(.*?)(## Tasks|$)', crew_md_content, re.DOTALL)
    if agents_match:
        agents_content = agents_match.group(1)
        agent_blocks = re.findall(r'### (.*?)\n(.*?)(?=### |$)', agents_content, re.DOTALL)
        
        if not agent_blocks:
            errors.append("No agents found in Agents section")
        else:
            agent_names = []
            for i, (name, details) in enumerate(agent_blocks):
                agent_names.append(name.strip())
                
                # Check required fields for each agent
                required_fields = ["Role", "Goal", "Backstory"]
                for field in required_fields:
                    if f"**{field}**" not in details:
                        errors.append(f"Agent {name} missing required field: **{field}**")
                
                # Check model format
                model_match = re.search(r'\*\*Model\*\*:\s*(.+)', details)
                if model_match:
                    model_name = model_match.group(1).strip()
                    if not model_name.startswith("ollama/") and model_name != "Default":
                        warnings.append(f"Agent {name} model '{model_name}' should use 'ollama/' prefix")
            
            # Check for duplicate agent names
            if len(agent_names) != len(set(agent_names)):
                errors.append("Duplicate agent names found")
    
    # Check Tasks section
    tasks_match = re.search(r'## Tasks(.*)', crew_md_content, re.DOTALL)
    if tasks_match:
        tasks_content = tasks_match.group(1)
        task_blocks = re.findall(r'### (.*?)\n(.*?)(?=### |$)', tasks_content, re.DOTALL)
        
        if not task_blocks:
            errors.append("No tasks found in Tasks section")
        else:
            task_names = []
            for i, (header, details) in enumerate(task_blocks):
                task_names.append(header.strip())
                
                # Extract task name (remove [Output: filename.md] if present)
                task_name = re.sub(r'\[Output:.*?\]', '', header).strip()
                
                # Check required fields
                required_fields = ["Description", "Expected Output", "Agent"]
                for field in required_fields:
                    if f"**{field}**" not in details:
                        errors.append(f"Task {task_name} missing required field: **{field}**")
                
                # Check if agent exists
                agent_match = re.search(r'\*\*Agent\*\*:\s*(.+)', details)
                if agent_match:
                    agent_name = agent_match.group(1).strip()
                    # This check would require knowing all agent names, we'll do it later
            
            # Check for duplicate task names
            if len(task_names) != len(set(task_names)):
                errors.append("Duplicate task names found")
    
    # Check for forbidden content
    forbidden_patterns = [
        (r'```python', "Python code blocks are not allowed in Crew.md"),
        (r'from crewai import', "Python imports are not allowed"),
        (r'Agent\(', "Python Agent instantiation is not allowed"),
        (r'Task\(', "Python Task instantiation is not allowed"),
        (r'Crew\(', "Python Crew instantiation is not allowed"),
    ]
    
    for pattern, message in forbidden_patterns:
        if re.search(pattern, crew_md_content):
            errors.append(message)
    
    # Check section headers format
    forbidden_headers = re.findall(r'^### [^A-Z]', crew_md_content, re.MULTILINE)
    if forbidden_headers:
        errors.append("Section headers after '###' should start with capital letter")
    
    return errors, warnings

def auto_correct_crew_md(crew_md_content):
    """Auto-correct common issues in Crew.md"""
    corrections = []
    
    # 1. Ensure Configuration section exists and has all required fields
    if "## Configuration" not in crew_md_content:
        # Try to find the title line and insert after it
        title_match = re.search(r'^(# Crew Team:.*)', crew_md_content, re.MULTILINE)
        if title_match:
            title_line = title_match.group(1)
            config_block = "\n\n## Configuration\n- Architecture: sequential\n- Supervisor Agent: None"
            crew_md_content = crew_md_content.replace(title_line, title_line + config_block)
            corrections.append("Added missing Configuration section after title")
        else:
            # Fallback: Prepend if no title found
            config_block = "# Crew Team: New Crew\n\n## Configuration\n- Architecture: sequential\n- Supervisor Agent: None\n\n"
            crew_md_content = config_block + crew_md_content
            corrections.append("Added missing Title and Configuration section at beginning")
    else:
        # Configuration section exists, check for mandatory fields
        config_match = re.search(r'## Configuration(.*?)(## Agents|## Tasks|$)', crew_md_content, re.DOTALL)
        if config_match:
            config_text = config_match.group(1)
            new_config_text = config_text
            
            if "Architecture" not in config_text:
                new_config_text += "\n- Architecture: sequential"
                corrections.append("Added missing 'Architecture' to Configuration")
            
            if "Supervisor Agent" not in config_text:
                new_config_text += "\n- Supervisor Agent: None"
                corrections.append("Added missing 'Supervisor Agent' to Configuration")
            
            if new_config_text != config_text:
                crew_md_content = crew_md_content.replace(config_text, new_config_text)

    # 2. Fix model format - add ollama/ prefix if missing, but avoid double prefixing
    model_pattern = r'(\*\*Model\*\*:\s*)(?!ollama/|Default)([^\n]+)'
    if re.search(model_pattern, crew_md_content):
        crew_md_content = re.sub(model_pattern, r'\1ollama/\2', crew_md_content)
        corrections.append("Added 'ollama/' prefix to model names")
    
    # 3. Fix section headers that don't start with capital
    header_pattern = r'^### ([a-z])'
    if re.search(header_pattern, crew_md_content, re.MULTILINE):
        def capitalize_header(match):
            return f"### {match.group(1).upper()}"
        crew_md_content = re.sub(header_pattern, capitalize_header, crew_md_content, flags=re.MULTILINE)
        corrections.append("Fixed section header capitalization")
    
    # 4. Ensure proper spacing after headers/sections
    crew_md_content = re.sub(r'(##? [^\n]+)\n+(?!#)', r'\1\n\n', crew_md_content)
    
    return crew_md_content, corrections

def create_crew(
    task_description, 
    model_name=None, 
    crew_context=None, 
    task_context=None,
    architecture="sequential",  # "sequential" or "hierarchical"
    enable_supervisor=False,    # Enable Supervisor agent with veto power
    enable_web_search=False,    # Enable web search for agents
    supervisor_model=None,      # Optional: different model for Supervisor (e.g., stronger model)
    output_dir=None,            # Optional: directory to save output files
    preview_mode=False,          # Preview mode without saving
    auto_correct=True,           # Enable auto-correction of common issues
    debug=False                 # Enable debug logging
):
    """
    Enhanced Crew Creation with Architecture Options and Strict Validation
    """
    if debug:
        setup_logging(output_dir)

    try:
        logging.info(f"Task: {task_description}")
        logging.info(f"Architecture: {architecture}, Supervisor: {enable_supervisor}, Web Search: {enable_web_search}")

        if model_name is None:
            model_name = OLLAMA_MODEL
        
        if supervisor_model is None:
            supervisor_model = model_name  # Use same as default if not specified
        
        mode = "Refining" if (crew_context or task_context) else "Creating"
        arch_info = f"{architecture.upper()}"
        if enable_supervisor:
            arch_info += " + SUPERVISOR"
        if enable_web_search:
            arch_info += " + WEB_SEARCH"
        
        print(f"--- {mode} Crew [{arch_info}] for: '{task_description}' ---")
        print(f"    Default Model: {model_name}")
        if enable_supervisor:
            print(f"    Supervisor Model: {supervisor_model}")

        # Local LLM with specified model
        current_llm = LLM(
            model=f"ollama/{model_name}",
            base_url=OLLAMA_BASE_URL
        )
        
        # Supervisor gets a potentially stronger model
        supervisor_llm = LLM(
            model=f"ollama/{supervisor_model}",
            base_url=OLLAMA_BASE_URL
        )

        # Read instructions and examples from script directory
        crew_instructions = ""
        crew_example = ""
        task_example = ""

        instruction_path = os.path.join(SCRIPT_DIR, "examples", "Crew_Instruction.md")
        if os.path.exists(instruction_path):
            with open(instruction_path, "r", encoding="utf-8") as f:
                crew_instructions = f.read()
        
        example_crew_path = os.path.join(SCRIPT_DIR, "examples", "Crew_Example.md")
        if os.path.exists(example_crew_path):
            with open(example_crew_path, "r", encoding="utf-8") as f:
                crew_example = f.read()

        example_task_path = os.path.join(SCRIPT_DIR, "examples", "Task_Example.md")
        if os.path.exists(example_task_path):
            with open(example_task_path, "r", encoding="utf-8") as f:
                task_example = f.read()
        
        # Load tools registry if Web Search is enabled
        architect_tools = []
        if enable_web_search:
            try:
                from tools_registry import get_tool_agent_tools
                available_tools = get_tool_agent_tools()
                architect_tools = available_tools # Give tools to Architect too
                tool_names = [tool.name for tool in available_tools]
                print(f"    Available tools for Agents & Architect: {', '.join(tool_names)}")
                logging.info(f"Loaded tools: {tool_names}")
            except Exception as e:
                print(f"    Warning: Could not load tools registry: {e}")
                logging.warning(f"Could not load tools: {e}")
                available_tools = []
        else:
            available_tools = []


        # Build architecture instructions
        architecture_instructions = build_architecture_instructions(
            architecture,
            enable_supervisor,
            enable_web_search,
            supervisor_model
        )

        # Define Meta-Agents
        architect = Agent(
            role="CrewAI Architect",
            goal=f"Design the most effective CrewAI team structure using {architecture} architecture. You can use web search tools to research the topic if needed to make better decisions.",
            backstory=f"You are a senior AI System Architect. You specialize in {architecture} team designs. "
                    f"You work with a strict custom markdown format, NOT Python code. "
                    f"If you need to understand the domain better, use your tools to research before designing.",
            llm=current_llm,
            tools=architect_tools,
            verbose=True,
            allow_delegation=False
        )

        writer = Agent(
            role="Configuration Writer",
            goal="Generate configuration files that EXACTLY match the provided example formats.",
            backstory="You are a technical writer who creates configuration files. You never explain yourself. You just output the file content.",
            llm=current_llm,
            verbose=True,
            allow_delegation=False
        )

        reviewer = Agent(
            role="Quality Assurance Specialist",
            goal="Validate correct formatting. Ensure NO PYTHON CODE is present.",
            backstory="You are a strict validator. You ensure the output matches the Example files structure exactly.",
            llm=current_llm,
            verbose=True,
            allow_delegation=False
        )

        # Task 1: Design the Crew with Architecture Awareness
        design_description = f"Analyze the request: '{task_description}'. \n"
        design_description += f"\nARCHITECTURE REQUIREMENTS:\n{architecture_instructions}\n"
        
        if enable_supervisor:
            design_description += "\nSUPERVISOR REQUIREMENTS:\n"
            design_description += "- Create a Supervisor agent that reviews outputs and provides quality gates\n"
            design_description += "- Supervisor can VETO outputs with specific feedback for correction\n"
            design_description += "- Add quality checkpoint tasks where Supervisor outputs 'APPROVED' or 'REVISE: [reason]'\n"
            design_description += "- Supervisor does NOT create content, only evaluates and guides\n"
            design_description += f"- Supervisor uses stronger model: {supervisor_model}\n"
        
        if enable_web_search:
            design_description += "\nWEB SEARCH REQUIREMENTS:\n"
            design_description += "- You have access to the 'brave_search' tool.\n"
            design_description += "- Identify which agents need external information (e.g., Researchers, Analysts, Market Specialists).\n"
            design_description += "- Assign the web search tool to these specific agents.\n"
            design_description += "- Specify tools in agent's Tools section like: **Tools**: brave_search\n"
            design_description += "- Do NOT assign tools to agents that don't need them (like Writers or Editors), unless they need to verify facts.\n"
        
        if crew_context or task_context:
            design_description += "\nThis is a REFINEMENT/UPDATE request based on existing configuration.\n"
            if crew_context:
                design_description += f"\nCurrent Crew Configuration:\n```markdown\n{crew_context}\n```\n"
            if task_context:
                design_description += f"\nCurrent Task Content:\n```markdown\n{task_context}\n```\n"
            design_description += f"\nBased on the user feedback above, MODIFY and IMPROVE the existing configuration while preserving its structure.\n"
        else:
            design_description += "Plan the Agents and Tasks needed.\n"
        
        design_description += f"Consider the structure used in this EXAMPLE of a good Crew:\n"
        design_description += f"```markdown\n{crew_example}\n```\n"
        
        design_task = Task(
            description=design_description,
            expected_output="A detailed plan for the agents and tasks with clear workflow.",
            agent=architect
        )

        # Task 2: Write Crew.md with Architecture Support
        write_crew_description = f"Write the 'Crew.md' file.\n"
        write_crew_description += "RULES:\n"
        write_crew_description += "1. OUTPUT MUST BE MARKDOWN, NOT PYTHON.\n"
        write_crew_description += f"2. Follow this EXACT format (Example):\n```markdown\n{crew_example}\n```\n"
        write_crew_description += f"3. Use the syntax rules:\n{crew_instructions}\n"
        write_crew_description += "4. Do not include ```markdown or ``` tags if possible, just the content.\n"
        write_crew_description += "5. IMPORTANT: Do NOT use '###' for section headers (e.g. '### Phase 1'). '###' is ONLY for Agent Names and Task Names. Use '**Bold**' for dividers.\n"
        
        # New: Add architecture configuration to Crew.md
        write_crew_description += "\n6. Include a '## Configuration' section at the very beginning of the Crew.md file, immediately after '# Crew Team:'.\n"
        write_crew_description += f"   - It must specify 'Architecture: {architecture}'.\n"
        if enable_supervisor:
            write_crew_description += f"   - It must specify 'Supervisor Agent: [The Name of the Supervisor Agent you create, e.g., 'Project Manager']'.\n"
            write_crew_description += "     - IMPORTANT: Identify the supervisor agent's name from the agent you create with the role of a supervisor/manager.\n"
        write_crew_description += "   - Example:\n     ```markdown\n     ## Configuration\n     - Architecture: sequential\n     - Supervisor Agent: None\n     ```\n"

        if enable_supervisor:
            write_crew_description += "\n7. SUPERVISOR IMPLEMENTATION:\n"
            write_crew_description += "   - Create a Supervisor agent (e.g., 'Editorial Director', 'Quality Guardian', 'Project Manager')\n"
            write_crew_description += f"   - Add line: **Model**: {supervisor_model}\n"
            write_crew_description += "   - Create checkpoint tasks like:\n"
            write_crew_description += "     ### Quality Gate: [Stage Name]\n"
            write_crew_description += "     - **Description**: Review [[previous_output.md]]. If quality is sufficient, output 'APPROVED'. If not, output 'REVISE: [specific actionable feedback]'.\n"
            write_crew_description += "     - **Expected Output**: Quality gate decision with clear reasoning\n"
            write_crew_description += "     - **Agent**: [Supervisor Name]\n"
        
        if enable_web_search:
            write_crew_description += "\n8. WEB SEARCH IMPLEMENTATION:\n"
            write_crew_description += "   - For agents that need to search the internet (identified in the design):\n"
            write_crew_description += "   - Add line: **Tools**: brave_search\n"
        
        # Load all available tools from registry for intelligent assignment
        available_tool_info = []
        try:
            from tools_registry import get_available_tools
            tool_info = get_available_tools()
            available_tool_info = tool_info.get('available_tools', [])
            logging.info(f"Loaded {len(available_tool_info)} tools for assignment")
        except Exception as e:
            logging.warning(f"Could not load tools info: {e}")

        if available_tool_info:
            write_crew_description += "\n\n9. TOOL ASSIGNMENT:\n"
            write_crew_description += "   Available tools in the system:\n"
            for tool in available_tool_info:
                write_crew_description += f"     - **{tool['name']}**: {tool['description']}\n"
            write_crew_description += "\n   Instructions:\n"
            write_crew_description += "   - Analyze the task description to identify which agents need which tools\n"
            write_crew_description += "   - Add this line to agents that need tools: **Tools**: tool_name1, tool_name2\n"
            write_crew_description += "   - Examples:\n"
            write_crew_description += "     * Agent downloading books → **Tools**: annas_archive_tool\n"
            write_crew_description += "     * Agent querying book content → **Tools**: ask_book_tool\n"
            write_crew_description += "     * Agent researching online → **Tools**: brave_search\n"
            write_crew_description += "   - Only assign tools that the agent actually needs for its tasks\n"
        
        if crew_context:
            write_crew_description += f"\nMODIFICATION MODE: Modify the existing Crew configuration below based on user feedback:\n"
            write_crew_description += f"```markdown\n{crew_context}\n```\n"
        
        write_crew_task = Task(
            description=write_crew_description,
            expected_output="The content for Crew.md with all specified architecture features, including the new Configuration section.",
            agent=writer
        )

        # Task 3: Review Crew.md with Architecture Validation
        review_crew_description = f"Review 'Crew.md'.\n"
        review_crew_description += f"1. It must start with '# Crew Team:'.\n"
        review_crew_description += f"2. It must have '## Configuration' section immediately after '# Crew Team:'.\n"
        review_crew_description += f"3. In '## Configuration': Verify 'Architecture: {architecture}' and 'Supervisor Agent: {'[Name]' if enable_supervisor else 'None'}'.\n"
        review_crew_description += f"4. It must have '## Agents' and '## Tasks'.\n"
        review_crew_description += f"5. It must NOT contain `from crewai import` or any Python code.\n"
        review_crew_description += f"6. It must match the structure of:\n```markdown\n{crew_example}\n```\n"
        review_crew_description += f"7. CHECK FOR FORBIDDEN HEADERS: If you see '### Phase 1' or similar, CHANGE it to '**Phase 1**' or remove it. '###' is only for Agents and Tasks.\n"
        
        if enable_supervisor:
            review_crew_description += "\n8. VERIFY SUPERVISOR:\n"
            review_crew_description += "   - Must have one Supervisor agent\n"
            review_crew_description += f"   - Supervisor must use model: {supervisor_model}\n"
            review_crew_description += "   - Must have quality gate tasks with APPROVED/REVISE logic\n"
            review_crew_description += "   - Supervisor tasks must NOT create content, only evaluate\n"
        
        if enable_web_search:
            review_crew_description += "\n9. VERIFY WEB SEARCH:\n"
            review_crew_description += "   - Ensure agents like Researchers have **Tools**: brave_search\n"
            review_crew_description += "   - Ensure the tool name is exactly 'brave_search'\n"
        
        # Add tool validation if tools are available
        if available_tool_info:
            review_crew_description += "\n\n10. VERIFY TOOL ASSIGNMENT:\n"
            review_crew_description += "   - Check if agents that need tools have **Tools**: field\n"
            review_crew_description += "   - Verify tool names match exactly (case-sensitive)\n"
            review_crew_description += f"   - Valid tool names: {', '.join([t['name'] for t in available_tool_info])}\n"
            review_crew_description += "   - Ensure tools are only assigned to agents that need them\n"
        
        review_crew_description += f"\nRefine it to be perfect."
        
        review_crew_task = Task(
            description=review_crew_description,
            expected_output="Clean, validated Crew.md content.",
            agent=reviewer,
            context=[write_crew_task]
        )

        # Task 4: Write Task.md
        write_task_description = f"Write the 'Task.md' file. The file should represent the user's main task for the generated crew.\n"
        write_task_description += "RULES:\n"
        write_task_description += "1. It MUST start with '# User Task for Agents'.\n"
        write_task_description += "2. After the header, you must ENHANCE and EXPAND the user's task description into a comprehensive, detailed task specification.\n"
        write_task_description += "3. The enhanced description should:\n"
        write_task_description += "   - Preserve the CORE INTENT and GOAL of the original user request\n"
        write_task_description += "   - Add relevant CONTEXT, DETAILS, and SPECIFICS that clarify what needs to be done\n"
        write_task_description += "   - Include CLEAR OBJECTIVES and EXPECTED OUTCOMES\n"
        write_task_description += "   - Specify any relevant CONSTRAINTS, REQUIREMENTS, or QUALITY STANDARDS\n"
        write_task_description += "   - Be written in a professional, clear, and actionable manner\n"
        write_task_description += "4. DO NOT add conversational filler, greetings, or meta-commentary. Just the enhanced task description.\n"
        write_task_description += f"5. Follow this format example as a quality reference:\n```markdown\n{task_example}\n```\n"
        write_task_description += "   Notice how the example is detailed, specific, and comprehensive while remaining focused.\n"
        
        if task_context:
            write_task_description += f"\nMODIFICATION MODE: Modify the existing Task content below based on user feedback:\n"
            write_task_description += f"```markdown\n{task_context}\n```\n"
            write_task_description += f"Your goal is to update and enhance the detailed task for the crew based on the feedback: '{task_description}'. The output should still be a complete Task.md file."
        else:
            write_task_description += f"\nThe user's original task request is: '{task_description}'\n"
            write_task_description += f"Your job is to transform this into a detailed, comprehensive task description that the crew can execute effectively.\n"
        
        write_task_input_task = Task(
            description=write_task_description,
            expected_output="The complete and correctly formatted content for Task.md, containing '# User Task for Agents' followed by an enhanced, detailed, and comprehensive task description that expands on the user's original request.",
            agent=writer
        )

        # Task 5: Review Task.md
        review_task_md_task = Task(
            description="Review 'Task.md'. Ensure it adheres to the format: '# User Task for Agents' followed by an enhanced, detailed task description. The description should be comprehensive and actionable, NOT just a simple copy of the user's brief input. No conversational filler.",
            expected_output="Clean, validated Task.md content with enhanced task description.",
            agent=reviewer,
            context=[write_task_input_task]
        )

        # Run Crew
        meta_crew = Crew(
            agents=[architect, writer, reviewer],
            tasks=[design_task, write_crew_task, review_crew_task, write_task_input_task, review_task_md_task],
            process=Process.sequential,
            verbose=True
        )

        logging.info("Starting Meta-Crew kickoff...")
        result = meta_crew.kickoff()
        logging.info("Meta-Crew kickoff completed.")
        
        # Save outputs
        crew_md_raw = str(review_crew_task.output.raw)
        task_md_raw = str(review_task_md_task.output.raw)

        crew_md_clean = clean_markdown(crew_md_raw)
        task_md_clean = clean_markdown(task_md_raw)

        # Apply auto-correction if enabled
        corrections = []
        if auto_correct:
            crew_md_clean, corrections = auto_correct_crew_md(crew_md_clean)
            if corrections:
                print("\n--- AUTO-CORRECTIONS APPLIED ---")
                for correction in corrections:
                    print(f"  - {correction}")

        # Validate generated Crew.md
        validation_errors, validation_warnings = validate_crew_md(crew_md_clean)
        
        if validation_errors:
            print(f"\n--- CREW.MD VALIDATION FAILED ---")
            for error in validation_errors:
                print(f"  ❌ {error}")
            logging.error(f"Crew.md validation failed: {validation_errors}")
            
            if not preview_mode:
                print("\nProceeding with generation despite validation errors...")
                logging.warning("Proceeding with generation despite validation errors.")
        
        if validation_warnings:
            print(f"\n--- CREW.MD VALIDATION WARNINGS ---")
            for warning in validation_warnings:
                print(f"  ⚠️  {warning}")

        if preview_mode:
            print("\n--- PREVIEW MODE ---")
            print("Generated Crew.md (first 1000 characters):")
            print("-" * 50)
            print(crew_md_clean[:1000] + "..." if len(crew_md_clean) > 1000 else crew_md_clean)
            print("-" * 50)
            
            print("\nGenerated Task.md (first 1000 characters):")
            print("-" * 50)
            print(task_md_clean[:1000] + "..." if len(task_md_clean) > 1000 else task_md_clean)
            print("-" * 50)
            
            if not preview_mode:
                print("\nProceeding to save files from preview...")
            else:
                response = input("\nWould you like to save these files? (Y/n): ")
                if response.lower() == 'n':
                    print("Files not saved.")
                    return

        print("\n--- Saving Configuration Files ---")

        # Determine output directory
        if output_dir:
            target_dir = output_dir
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
        else:
            target_dir = os.getcwd()

        # Save to target directory
        crew_path = os.path.join(target_dir, "Crew.md")
        with open(crew_path, "w", encoding="utf-8") as f:
            f.write(crew_md_clean)
            print(f"Created {crew_path}")
        
        task_path = os.path.join(target_dir, "Task.md")
        with open(task_path, "w", encoding="utf-8") as f:
            f.write(task_md_clean)
            print(f"Created {task_path}")

        print("\n--- ARCHITECTURE SUMMARY ---")
        print(f"Architecture: {architecture}")
        print(f"Supervisor: {'ENABLED' if enable_supervisor else 'DISABLED'}")
        print(f"Web Search: {'ENABLED' if enable_web_search else 'DISABLED'}")
        print("\nSuccess! You can now run the crew with: python script/run_crew.py")

    except Exception as e:
        logging.critical("CRITICAL ERROR during creation:", exc_info=True)
        print(f"\n❌ FATAL ERROR: {str(e)}")
        print(f"See {os.path.join(output_dir if output_dir else os.getcwd(), 'create_debug.log')} for details.")
        raise

def build_architecture_instructions(architecture, enable_supervisor, enable_web_search, supervisor_model):
    """Build detailed instructions for the requested architecture."""
    
    instructions = f"\n**ARCHITECTURE TYPE: {architecture.upper()}**\n"
    
    if architecture == "sequential":
        instructions += """
- Tasks execute in LINEAR ORDER: Task 1 → Task 2 → Task 3
- Each task completes before the next begins
- Agents work independently in sequence
- Use when: steps depend on previous results
"""
    
    elif architecture == "hierarchical":
        instructions += """
- SUPERVISOR coordinates all work
- Supervisor reviews and approves outputs
- Supervisor provides strategic direction
- Workers execute under supervisor guidance
- Use when: need central oversight and quality control
"""
        if enable_supervisor:
            instructions += f"""
**SUPERVISOR DETAILS:**
- Model: {supervisor_model} (potentially stronger for better judgment)
- Role: Oversees workflow, validates quality, provides guidance
- Powers: Can VETO outputs with specific feedback
- Tasks: Quality gates that output APPROVED or REVISE: [reason]
- Does NOT: Create content, only evaluates and directs
"""
    
    if enable_web_search:
        instructions += """
**WEB SEARCH CAPABILITY:**
- You have access to the 'brave_search' tool.
- Assign this tool to agents that need to find fresh information (like Researchers).
- Usage in Crew.md: **Tools**: brave_search
"""
    
    return instructions

if __name__ == "__main__":
    import argparse
    import re
    
    parser = argparse.ArgumentParser(
        description="Create CrewAI configuration with architecture options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple sequential crew
  python create_crew.py "Write a story about AI"
  
  # Hierarchical with supervisor
  python create_crew.py "Research and write report" --architecture hierarchical --supervisor
  
  # Full featured: hierarchical + supervisor + web search + custom model
  python create_crew.py "Complex research project" \\
      --architecture hierarchical \\
      --supervisor \\
      --supervisor-model llama3.1:70b \\
      --web-search \\
      --model llama3.1:8b
  
  # Preview mode without saving
  python create_crew.py "Test task" --preview
        """
    )
    
    parser.add_argument(
        "task_description",
        help="Description of the task for the crew to perform"
    )
    
    parser.add_argument(
        "--model",
        default=None,
        help="Default model for all agents (e.g., llama3, mistral:7b)"
    )
    
    parser.add_argument(
        "--architecture",
        choices=["sequential", "hierarchical"],
        default="sequential",
        help="Workflow architecture type (default: sequential)"
    )
    
    parser.add_argument(
        "--supervisor",
        action="store_true",
        help="Enable Supervisor agent with veto power"
    )
    
    parser.add_argument(
        "--supervisor-model",
        default=None,
        help="Specific model for Supervisor (e.g., llama3.1:70b for better judgment)"
    )
    
    parser.add_argument(
      "--web-search",
      action="store_true",
      help="Enable web search capabilities for agents"
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to save generated files"
    )
    
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview mode without saving files"
    )
    
    parser.add_argument(
        "--no-auto-correct",
        action="store_true",
        help="Disable auto-correction of common issues"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    create_crew(
        task_description=args.task_description,
        model_name=args.model,
        architecture=args.architecture,
        enable_supervisor=args.supervisor,
        enable_web_search=args.web_search,
        supervisor_model=args.supervisor_model,
        output_dir=args.output_dir,
        preview_mode=args.preview,
        auto_correct=not args.no_auto_correct,
        debug=args.debug
    )