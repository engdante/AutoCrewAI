import re
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
INPUT_DIR = os.path.join(PROJECT_ROOT, "input")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

def parse_crew_md(file_path, task_input_content):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse Crew Title
    title_match = re.search(r'^# Crew Team: (.*)', content, re.MULTILINE)
    crew_title = title_match.group(1).strip() if title_match else "Unnamed Crew"

    # Split into Agents and Tasks sections
    agents_section = re.search(r'## Agents(.*?)(## Tasks|$)', content, re.DOTALL)
    tasks_section = re.search(r'## Tasks(.*)', content, re.DOTALL)

    agents = {}
    if agents_section:
        agent_blocks = re.findall(r'### (.*?)\n(.*?)(?=### |$)', agents_section.group(1), re.DOTALL)
        for name, details in agent_blocks:
            name = name.strip()
            role = re.search(r'- \*\*Role\*\*: (.*)', details)
            goal = re.search(r'- \*\*Goal\*\*: (.*)', details)
            backstory = re.search(r'- \*\*Backstory\*\*: (.*)', details)
            custom_model = re.search(r'- \*\*Model\*\*: (.*)', details)
            
            # Determine which LLM to use
            if custom_model:
                model_name = custom_model.group(1).strip()
                agent_llm = LLM(
                    model=f"ollama/{model_name}",
                    base_url=OLLAMA_BASE_URL
                )
                print(f"Agent {name} using custom model: {model_name}")
            else:
                agent_llm = ollama_llm # Default from config
            
            agents[name] = Agent(
                role=role.group(1).strip() if role else "",
                goal=goal.group(1).strip() if goal else "",
                backstory=backstory.group(1).strip() if backstory else "",
                llm=agent_llm,  
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

            description = re.search(r'- \*\*Description\*\*: (.*)', details)
            expected_output = re.search(r'- \*\*Expected Output\*\*: (.*)', details)
            agent_name = re.search(r'- \*\*Agent\*\*: (.*)', details)
            
            agent_inst = agents.get(agent_name.group(1).strip()) if agent_name else None
            
            if agent_inst:
                desc_text = description.group(1).strip() if description else ""
                
                # Injection 1: {task_input} from Task.md
                if "{task_input}" in desc_text:
                    desc_text = desc_text.replace("{task_input}", task_input_content)
                elif task_input_content:
                    # Only prepend if no explicit placeholder AND Task.md is not empty
                    desc_text = f"Context from Task.md:\n{task_input_content}\n\nTask Description: {desc_text}"

                # Injection 2: Dynamic [[filename]] support
                file_placeholders = re.findall(r'\[\[(.*?)\]\]', desc_text)
                for f_name in file_placeholders:
                    f_name = f_name.strip()
                    # Look for file in input directory first, then project root
                    input_path = os.path.join(INPUT_DIR, f_name)
                    root_path = os.path.join(PROJECT_ROOT, f_name)
                    
                    file_path = None
                    if os.path.exists(input_path):
                        file_path = input_path
                    elif os.path.exists(root_path):
                        file_path = root_path
                    
                    if file_path:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            f_content = f.read()
                        
                        # Apply sampling if the file is large
                        if len(f_content) > 50000:
                            print(f"Sampling large file: {f_name}")
                            chunk = 15000
                            f_content = (
                                f"[NOTE: Content of {f_name} has been sampled due to size]\n\n"
                                f"--- START OF FILE ---\n{f_content[:chunk]}\n\n"
                                f"--- MIDDLE OF FILE ---\n{f_content[len(f_content)//2 - chunk//2 : len(f_content)//2 + chunk//2]}\n\n"
                                f"--- END OF FILE ---\n{f_content[-chunk:]}"
                            )
                        
                        desc_text = desc_text.replace(f"[[{f_name}]]", f_content)
                        print(f"Injected content from {file_path}")
                    else:
                        print(f"Warning: File [[{f_name}]] not found in input/ or project root.")

                tasks_data.append({
                    "name": task_name,
                    "custom_output": custom_output_file,
                    "task": Task(
                        description=desc_text,
                        expected_output=expected_output.group(1).strip() if expected_output else "",
                        agent=agent_inst
                    )
                })

    return crew_title, list(agents.values()), tasks_data

def run_crew(crew_file, task_file):
    print(f"--- Loading Crew from {crew_file} ---")
    
    task_input_content = ""
    if os.path.exists(task_file):
        with open(task_file, 'r', encoding='utf-8') as f:
            task_input_content = f.read()
    
    title, agents, tasks_data = parse_crew_md(crew_file, task_input_content)
    
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
        with open(feedback_path, "r", encoding="utf-8") as f:
            feedback_content = f.read()
        
        for td in tasks_data:
            # Inject into the Enrichment/Development task
            if any(k in td["name"].lower() for k in ["enrich", "develop", "write"]):
                print(f"--- [INJECT] Injecting feedback into '{td['name']}' ---")
                td["task"].description = f"PREVIOUS EDITORIAL FEEDBACK TO ADDRESS:\n{feedback_content}\n\n{td['task'].description}"
                # We only inject into the first matching task (the main production one)
                break

    if not agents or not tasks_data:
        print("Error: No agents or tasks found. Check your Crew.md syntax.")
        return

    print(f"Starting Crew: {title}")
    
    crew = Crew(
        agents=agents,
        tasks=[td["task"] for td in tasks_data],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()
    
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

if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in environment variables.")
    
    # Look for Crew.md and Task.md in project root
    crew_file = os.path.join(PROJECT_ROOT, 'Crew.md')
    task_file = os.path.join(PROJECT_ROOT, 'Task.md')
    run_crew(crew_file, task_file)
