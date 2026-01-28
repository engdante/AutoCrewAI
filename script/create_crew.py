import os
import sys
import warnings

# Suppress Pydantic V2 compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pydantic')
# Suppress CrewAI Tracing/Telemetry messages
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"

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

# Initialize LLM with Ollama configuration
ollama_llm = LLM(
    model=f"ollama/{OLLAMA_MODEL}",
    base_url=OLLAMA_BASE_URL
)

def clean_markdown(content):
    """Removes markdown code block formatting if present."""
    if content.startswith("```"):
        # Remove first line
        content = "\n".join(content.split("\n")[1:])
        # Remove last line if it is just backticks
        if content.strip().endswith("```"):
             content = content.replace("```", "").strip() # Aggressive cleanup at end
    return content.strip()

def create_crew(
    task_description, 
    model_name=None, 
    crew_context=None, 
    task_context=None,
    architecture="sequential",  # "sequential" or "hierarchical"
    enable_supervisor=False,    # Enable Supervisor agent with veto power
    enable_tool_agent=False,    # Enable dedicated Tool Agent
    supervisor_model=None       # Optional: different model for Supervisor (e.g., stronger model)
):
    """
    Enhanced Crew Creation with Architecture Options
    
    Parameters:
    -----------
    task_description : str
        The main task to create crew for
    model_name : str, optional
        Default model for all agents
    crew_context : str, optional
        Existing Crew.md content for refinement
    task_context : str, optional
        Existing Task.md content for refinement
    architecture : str
        "sequential" - Linear workflow
        "hierarchical" - Supervisor coordinates workflow
    enable_supervisor : bool
        Add Supervisor agent with quality gates and veto power
    enable_tool_agent : bool
        Add dedicated Tool Agent for all external operations
    supervisor_model : str, optional
        Specific model for Supervisor (recommended: stronger model like llama3.1:70b)
    
    Examples:
    ---------
    # Simple sequential crew
    create_crew("Write a story", architecture="sequential")
    
    # Hierarchical with Supervisor and Tool Agent
    create_crew("Research and write", 
                architecture="hierarchical",
                enable_supervisor=True,
                enable_tool_agent=True,
                supervisor_model="llama3.1:70b")
    """
    
    if model_name is None:
        model_name = OLLAMA_MODEL
    
    if supervisor_model is None:
        supervisor_model = model_name  # Use same as default if not specified
    
    mode = "Refining" if (crew_context or task_context) else "Creating"
    arch_info = f"{architecture.upper()}"
    if enable_supervisor:
        arch_info += " + SUPERVISOR"
    if enable_tool_agent:
        arch_info += " + TOOL_AGENT"
    
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
    
    # Load tools registry if Tool Agent is enabled
    tools_info = ""
    if enable_tool_agent:
        tools_registry_path = os.path.join(SCRIPT_DIR, "tools_registry.py")
        if os.path.exists(tools_registry_path):
            with open(tools_registry_path, "r", encoding="utf-8") as f:
                tools_info = f.read()
            print(f"    Loaded tools registry")

    # Build architecture instructions
    architecture_instructions = build_architecture_instructions(
        architecture,
        enable_supervisor,
        enable_tool_agent,
        supervisor_model
    )

    # Define Meta-Agents
    architect = Agent(
        role="CrewAI Architect",
        goal=f"Design the most effective CrewAI team structure using {architecture} architecture.",
        backstory=f"You are a senior AI System Architect. You specialize in {architecture} team designs. "
                  f"You work with a strict custom markdown format, NOT Python code.",
        llm=current_llm,
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
    
    if enable_tool_agent:
        design_description += "\nTOOL AGENT REQUIREMENTS:\n"
        design_description += "- Create a Tool Agent (e.g., 'Research Assistant', 'Information Specialist')\n"
        design_description += "- This agent handles ALL external operations: web search, file reading, data extraction\n"
        design_description += "- Other agents request information from Tool Agent instead of accessing tools directly\n"
        design_description += "- Tool Agent should have access to these confirmed tools:\n"
        design_description += "  * FileReadTool (read files)\n"
        design_description += "  * WebsiteSearchTool (search websites)\n"
        design_description += "  * SerperDevTool (web search - requires API key)\n"
        design_description += "- Specify tools in agent's Tools section like: **Tools**: FileReadTool, WebsiteSearchTool\n"
    
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
    
    if enable_supervisor:
        write_crew_description += "\n6. SUPERVISOR IMPLEMENTATION:\n"
        write_crew_description += "   - Create a Supervisor agent (e.g., 'Editorial Director', 'Quality Guardian', 'Project Manager')\n"
        write_crew_description += f"   - Add line: **Model**: {supervisor_model}\n"
        write_crew_description += "   - Create checkpoint tasks like:\n"
        write_crew_description += "     ### Quality Gate: [Stage Name]\n"
        write_crew_description += "     - **Description**: Review [[previous_output.md]]. If quality is sufficient, output 'APPROVED'. If not, output 'REVISE: [specific actionable feedback]'.\n"
        write_crew_description += "     - **Expected Output**: Quality gate decision with clear reasoning\n"
        write_crew_description += "     - **Agent**: [Supervisor Name]\n"
    
    if enable_tool_agent:
        write_crew_description += "\n7. TOOL AGENT IMPLEMENTATION:\n"
        write_crew_description += "   - Create a Tool Agent (e.g., 'Research Assistant', 'Information Gatherer')\n"
        write_crew_description += "   - Add line: **Tools**: FileReadTool, WebsiteSearchTool\n"
        write_crew_description += "   - This agent handles all file reading, web searches, and data extraction\n"
        write_crew_description += "   - Other agents reference Tool Agent's outputs using [[tool_output.md]]\n"
    
    if crew_context:
        write_crew_description += f"\nMODIFICATION MODE: Modify the existing Crew configuration below based on user feedback:\n"
        write_crew_description += f"```markdown\n{crew_context}\n```\n"
    
    write_crew_task = Task(
        description=write_crew_description,
        expected_output="The content for Crew.md with all specified architecture features.",
        agent=writer
    )

    # Task 3: Review Crew.md with Architecture Validation
    review_crew_description = f"Review 'Crew.md'.\n"
    review_crew_description += f"1. It must start with '# Crew Team:'.\n"
    review_crew_description += f"2. It must have '## Agents' and '## Tasks'.\n"
    review_crew_description += f"3. It must NOT contain `from crewai import` or any Python code.\n"
    review_crew_description += f"4. It must match the structure of:\n```markdown\n{crew_example}\n```\n"
    review_crew_description += f"5. CHECK FOR FORBIDDEN HEADERS: If you see '### Phase 1' or similar, CHANGE it to '**Phase 1**' or remove it. '###' is only for Agents and Tasks.\n"
    
    if enable_supervisor:
        review_crew_description += "\n6. VERIFY SUPERVISOR:\n"
        review_crew_description += "   - Must have one Supervisor agent\n"
        review_crew_description += f"   - Supervisor must use model: {supervisor_model}\n"
        review_crew_description += "   - Must have quality gate tasks with APPROVED/REVISE logic\n"
        review_crew_description += "   - Supervisor tasks must NOT create content, only evaluate\n"
    
    if enable_tool_agent:
        review_crew_description += "\n7. VERIFY TOOL AGENT:\n"
        review_crew_description += "   - Must have one Tool Agent\n"
        review_crew_description += "   - Tool Agent must list: **Tools**: FileReadTool, WebsiteSearchTool\n"
        review_crew_description += "   - Other agents should reference Tool Agent's outputs\n"
    
    review_crew_description += f"\nRefine it to be perfect."
    
    review_crew_task = Task(
        description=review_crew_description,
        expected_output="Clean, validated Crew.md content.",
        agent=reviewer,
        context=[write_crew_task]
    )

    # Task 4: Write Task.md
    write_task_description = f"Write the 'Task.md' file.\n"
    write_task_description += "1. It must start with '# User Task for Agents'.\n"
    write_task_description += f"2. Follow this format:\n```markdown\n{task_example}\n```\n"
    write_task_description += "3. Include the detailed prompt for the crew.\n"
    
    if task_context:
        write_task_description += f"\nMODIFICATION MODE: Modify the existing Task content below based on user feedback:\n"
        write_task_description += f"```markdown\n{task_context}\n```\n"
    
    write_task_input_task = Task(
        description=write_task_description,
        expected_output="The content for Task.md.",
        agent=writer
    )

    # Task 5: Review Task.md
    review_task_md_task = Task(
        description="Review 'Task.md'. Ensure it adheres to the format: '# User Task for Agents' followed by the text. No conversational filler.",
        expected_output="Clean Task.md content.",
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

    result = meta_crew.kickoff()
    
    # Save outputs
    crew_md_raw = str(review_crew_task.output.raw)
    task_md_raw = str(review_task_md_task.output.raw)

    crew_md_clean = clean_markdown(crew_md_raw)
    task_md_clean = clean_markdown(task_md_raw)

    print("\n--- Saving Configuration Files ---")

    # Save to project root
    crew_path = os.path.join(PROJECT_ROOT, "Crew.md")
    with open(crew_path, "w", encoding="utf-8") as f:
        f.write(crew_md_clean)
        print(f"Created {crew_path}")
    
    task_path = os.path.join(PROJECT_ROOT, "Task.md")
    with open(task_path, "w", encoding="utf-8") as f:
        f.write(task_md_clean)
        print(f"Created {task_path}")

    print("\n--- ARCHITECTURE SUMMARY ---")
    print(f"Architecture: {architecture}")
    print(f"Supervisor: {'ENABLED' if enable_supervisor else 'DISABLED'}")
    print(f"Tool Agent: {'ENABLED' if enable_tool_agent else 'DISABLED'}")
    print("\nSuccess! You can now run the crew with: python script/run_crew.py")

def build_architecture_instructions(architecture, enable_supervisor, enable_tool_agent, supervisor_model):
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
    
    if enable_tool_agent:
        instructions += """
**TOOL AGENT (Centralized):**
- One agent handles ALL external operations
- Responsibilities: web search, file reading, data extraction
- Available tools: FileReadTool, WebsiteSearchTool, SerperDevTool
- Other agents REQUEST information from Tool Agent
- Benefits: No duplicate searches, consistent formatting, easier debugging
"""
    
    return instructions

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create CrewAI configuration with architecture options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple sequential crew
  python create_crew.py "Write a story about AI"
  
  # Hierarchical with supervisor
  python create_crew.py "Research and write report" --architecture hierarchical --supervisor
  
  # Full featured: hierarchical + supervisor + tool agent + custom model
  python create_crew.py "Complex research project" \\
      --architecture hierarchical \\
      --supervisor \\
      --supervisor-model llama3.1:70b \\
      --tool-agent \\
      --model llama3.1:8b
  
  # Sequential with tool agent only
  python create_crew.py "Process documents" --tool-agent
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
        "--tool-agent",
        action="store_true",
        help="Enable dedicated Tool Agent for all external operations"
    )
    
    args = parser.parse_args()
    
    create_crew(
        task_description=args.task_description,
        model_name=args.model,
        architecture=args.architecture,
        enable_supervisor=args.supervisor,
        enable_tool_agent=args.tool_agent,
        supervisor_model=args.supervisor_model
    )
