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

def create_crew(task_description, model_name=None, crew_context=None, task_context=None):
    if model_name is None:
        model_name = OLLAMA_MODEL
    
    mode = "Refining" if (crew_context or task_context) else "Creating"
    print(f"--- {mode} Crew for: '{task_description}' using model: '{model_name}' ---")

    # Local LLM with specified model
    current_llm = LLM(
        model=f"ollama/{model_name}",
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

    # Define Meta-Agents
    architect = Agent(
        role="CrewAI Architect",
        goal="Design the most effective CrewAI team structure (Agents and Tasks) for a given user objective.",
        backstory="You are a senior AI System Architect. You design teams of AI agents. You work with a strict custom markdown format, NOT Python code.",
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

    # Define Meta-Tasks (rest remains same but using current_llm by reference through agents)
    # Task 1: Design the Crew
    design_description = f"Analyze the request: '{task_description}'. \n"
    
    if crew_context or task_context:
        design_description += "This is a REFINEMENT/UPDATE request based on existing configuration.\n"
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
        expected_output="A plan for the agents and tasks.",
        agent=architect
    )

    # Task 2: Write Crew.md
    write_crew_description = f"Write the 'Crew.md' file.\n"
    write_crew_description += "RULES:\n"
    write_crew_description += "1. OUTPUT MUST BE MARKDOWN, NOT PYTHON.\n"
    write_crew_description += f"2. Follow this EXACT format (Example):\n```markdown\n{crew_example}\n```\n"
    write_crew_description += f"3. Use the syntax rules:\n{crew_instructions}\n"
    write_crew_description += "4. Do not include ```markdown or ``` tags if possible, just the content.\n"
    write_crew_description += "5. IMPORTANT: Do NOT use '###' for section headers (e.g. '### Phase 1'). '###' is ONLY for Agent Names and Task Names. Use '**Bold**' for dividers.\n"
    
    if crew_context:
        write_crew_description += f"\nMODIFICATION MODE: Modify the existing Crew configuration below based on user feedback:\n"
        write_crew_description += f"```markdown\n{crew_context}\n```\n"
    
    write_crew_task = Task(
        description=write_crew_description,
        expected_output="The content for Crew.md.",
        agent=writer
    )

    # Task 3: Review Crew.md
    review_crew_task = Task(
        description=f"Review 'Crew.md'.\n"
                    f"1. It must start with '# Crew Team:'.\n"
                    f"2. It must have '## Agents' and '## Tasks'.\n"
                    f"3. It must NOT contain `from crewai import` or any Python code.\n"
                    f"4. It must match the structure of:\n```markdown\n{crew_example}\n```\n"
                    f"5. CHECK FOR FORBIDDEN HEADERS: If you see '### Phase 1' or similar, CHANGE it to '**Phase 1**' or remove it. '###' is only for Agents and Tasks.\n"
                    f"Refine it to be perfect.",
        expected_output="Clean Crew.md content.",
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

    print("\nSuccess! You can now run the crew with: python script/run_crew.py")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_crew.py \"<task_description>\" [model_name]")
        print("Example: python create_crew.py \"Write a story about a toaster\" llama3")
    else:
        # If there are at least 2 args, let's see if the last one is likely a model name
        # We'll assume the last arg is the model name if there's more than 1 arg
        if len(sys.argv) > 2:
            description = sys.argv[1]
            model = sys.argv[2]
        else:
            description = sys.argv[1]
            model = None
            
        create_crew(description, model)
