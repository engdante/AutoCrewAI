# CrewAI GUI & Automation System

## Project Overview
This project is an advanced automation system for managing and executing CrewAI agent teams. It provides a graphical user interface (GUI) to define agents and tasks, and uses a meta-agent "Architect" flow to generate the necessary Markdown configurations (`Crew.md` and `Task.md`). The system bridges the gap between high-level human objectives and executable AI workflows.

## Core Logic & Features

1.  **GUI-Driven Configuration**: A comprehensive `tkinter` interface ([app.py](file:///d:/AI/crewAI/app.py)) allows users to:
    -   Manage Agent properties (Role, Goal, Backstory, individual Model selection).
    -   Define Tasks and route their outputs.
    -   Configure environment settings (.env) directly from the UI.
    -   Monitor execution logs in real-time.

2.  **Meta-Agent Generation**: The system uses a specialized script ([create_crew.py](file:///d:/AI/crewAI/create_crew.py)) where a "Meta-Crew" (Architect, Writer, Reviewer) analyzes a user request and generates the `Crew.md` and `Task.md` files automatically.

3.  **Advanced Parsing & Execution**: The execution engine ([run_crew.py](file:///d:/AI/crewAI/script/run_crew.py)) features:
    -   **Context Injection**: Automatically injects content from `Task.md` or local files referenced via `[[filename]]`.
    -   **Input Directory**: Files referenced with `[[filename]]` are searched in the `input/` directory first, then project root.
    -   **File Sampling**: Large files are automatically sampled (start, middle, end) to stay within LLM context limits.
    -   **Dynamic Output Routing**: Tasks can define custom output filenames using the `[Output: filename.md]` syntax in headers.
    -   **Output Directory**: All generated files are saved to the `output/` directory.
    -   **Task Skipping**: Optional logic to skip tasks if their output already exists (e.g., style guides).

4.  **Multi-LLM Support**: Each agent can be assigned a specific Ollama model. Configuration is managed via environment variables and the GUI.

## Project Structure

### Root Directory
-   [app.py](file:///d:/AI/crewAI/app.py): The main GUI application. Entry point for configuration and execution.
-   [.env](file:///d:/AI/crewAI/.env): Stores server IP, port, default model, and API keys.
-   [Crew.md](file:///d:/AI/crewAI/Crew.md): The current team definition (generated or manually edited).
-   [Task.md](file:///d:/AI/crewAI/Task.md): The specific objective for the current run.
-   [Project_Specs.md](file:///d:/AI/crewAI/Project_Specs.md): This documentation file.
-   [requirements.txt](file:///d:/AI/crewAI/requirements.txt): Python dependencies.

### script/ Directory
-   [create_crew.py](file:///d:/AI/crewAI/script/create_crew.py): Generates Markdown configurations using meta-agents.
-   [run_crew.py](file:///d:/AI/crewAI/script/run_crew.py): Parses Markdown files and executes the actual CrewAI team.
-   [Crew_Instruction.md](file:///d:/AI/crewAI/script/Crew_Instruction.md): Strict syntax rules for the `Crew.md` parser.
-   **examples/**: Example configuration files used by `create_crew.py`
    -   `Crew_Example.md`: Example crew configuration
    -   `Task_Example.md`: Example task configuration
    -   `.env.example`: Example environment configuration

### input/ Directory
Files that users want to provide to the crew. When using `[[filename]]` in task descriptions, the system looks here first.
-   Example: `book.txt`, `chapter.txt`

### output/ Directory
Generated outputs from crew execution:
-   `Task_Plan.md`: Strategy and planning documents.
-   `Task_Result.md`: Final product or execution output.
-   `Task_Feedback.md`: Review and evaluation logs.
-   `book_summary.md`: Style analysis (if applicable).
-   Any custom files specified with `[Output: filename.md]` syntax.

## Setup & Usage
1.  **Dependencies**: `pip install crewai litellm python-dotenv`
2.  **Configuration**: Open the GUI ([app.py](file:///d:/AI/crewAI/app.py)) and use the "Settings" menu to configure your Ollama server and models.
3.  **Workflow**:
    -   Click **"Generate Crew"** to describe your goal and let meta-agents build the team.
    -   Review/Edit the generated agents and tasks in the main window.
    -   Click **"Run Crew"** to execute.

## Key Syntax (Crew.md)
-   **Headers**: `# Crew Team`, `## Agents`, `### [Agent Name]`, `## Tasks`, `### [Task Name] [Output: file.md]`.
-   **Properties**: `**Role**`, `**Goal**`, `**Backstory**`, `**Model**`, `**Description**`, `**Expected Output**`, `**Agent**`.
-   **Placeholders**: 
    -   `{task_input}` for `Task.md` content
    -   `[[filename]]` for external file content (searches in `input/` directory first, then project root)
