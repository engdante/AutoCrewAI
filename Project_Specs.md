# CrewAI GUI & Automation System

## Project Overview
This project is an advanced automation system for managing and executing CrewAI agent teams. It provides a comprehensive graphical user interface (GUI) built with tkinter that allows users to define agents and tasks, and uses a meta-agent "Architect" flow to automatically generate optimized Markdown configurations (`Crew.md` and `Task.md`). The system bridges the gap between high-level human objectives and executable AI workflows.

## Core Features

### 1. GUI-Driven Configuration
A comprehensive `tkinter` interface ([app.py](file:///d:/AI/crewAI/app.py)) provides:
- **Multi-Crew Management**: Create, rename, and switch between multiple crew configurations
- **Agent Management**: Define agent properties (Role, Goal, Backstory, individual Model selection)
- **Task Definition**: Create tasks with custom output routing and agent assignment
- **Environment Settings**: Configure Ollama server, models, and API keys directly from the UI
- **Real-time Execution Monitoring**: View execution logs in a dedicated window with progress indicators
- **Model Discovery**: Automatic detection and listing of available Ollama models

### 2. Meta-Agent Generation System
The system uses a specialized script ([create_crew.py](file:///d:/AI/crewAI/script/create_crew.py)) where a "Meta-Crew" analyzes user requests and generates optimized configurations:

**Meta-Agents:**
- **Architect**: Designs the most effective team structure based on the task
- **Writer**: Generates configuration files following strict format rules
- **Reviewer**: Validates and refines the output for correctness

**Generation Features:**
- **Architecture Support**: Sequential or Hierarchical workflows
- **Supervisor Mode**: Optional supervisor agent with quality gates and veto power
- **Tool Agent Mode**: Dedicated agent for all external operations (web search, file reading)
- **Enhanced Task Descriptions**: AI automatically expands brief user requests into detailed, comprehensive task specifications
- **Refinement Mode**: Iteratively improve existing crews based on feedback

### 3. Advanced Parsing & Execution Engine
The execution engine ([run_crew.py](file:///d:/AI/crewAI/script/run_crew.py)) features:

**Context Injection:**
- `{task_input}`: Automatically injects content from `Task.md`
- `[[filename]]`: Dynamically loads external files (searches `input/` directory first, then project root)
- **Smart File Sampling**: Large files (>50KB) are automatically sampled (start, middle, end) to stay within LLM context limits

**Dynamic Output Routing:**
- Custom output files via `[Output: filename.md]` syntax in task headers
- Keyword-based automatic routing (plan → Task_Plan.md, result → Task_Result.md, feedback → Task_Feedback.md)
- All outputs saved to crew-specific `output/` directory

**Intelligent Task Management:**
- **Task Skipping**: Skip tasks if their output already exists (e.g., style guides)
- **Output Injection**: Reuse existing outputs in subsequent tasks
- **Feedback Loop**: Automatically inject previous feedback into enrichment tasks

**Architecture Support:**
- **Sequential**: Linear task execution (Task 1 → Task 2 → Task 3)
- **Hierarchical**: Supervisor-coordinated workflow with quality control

### 4. Multi-LLM Support
- Each agent can use a different Ollama model
- Configuration via environment variables and GUI
- Model selection with automatic discovery from Ollama server
- Support for specialized models (e.g., stronger model for supervisor)

### 5. Tools Registry System
A comprehensive tools management system ([tools_registry.py](file:///d:/AI/crewAI/script/tools_registry.py)) provides:
- **Tool Categorization**: Search Tools, File Tools, Data Tools, Custom Tools
- **Intelligent Tool Selection**: Automatic tool assignment based on agent roles and task context
- **Tool Testing Framework**: Structured validation before integration
- **Metadata Management**: Requirements, cost, suitability, and trigger keywords for each tool
- **Extensible Architecture**: Support for both crewai-tools and custom-built tools

## Project Structure

### Root Directory
- **[app.py](file:///d:/AI/crewAI/app.py)**: Main GUI application - entry point for all operations
- **[.env](file:///d:/AI/crewAI/.env)**: Environment configuration (Ollama server, port, default model, API keys)
- **[requirements.txt](file:///d:/AI/crewAI/requirements.txt)**: Python dependencies
- **[Project_Specs.md](file:///d:/AI/crewAI/Project_Specs.md)**: This technical documentation
- **[README.md](file:///d:/AI/crewAI/README.md)**: User-facing setup and usage guide

### crews/ Directory
Each crew has its own subdirectory containing:
- **Crew.md**: Team definition (agents and tasks)
- **Task.md**: Enhanced task description for the crew
- **crew.json**: Metadata (name, description, folder)
- **input/**: Files for the crew to process
- **output/**: Generated results from crew execution

Example structure:
```
crews/
├── default/
│   ├── Crew.md
│   ├── Task.md
│   ├── crew.json
│   ├── input/
│   └── output/
├── Idea Creator/
│   ├── Crew.md
│   ├── Task.md
│   ├── crew.json
│   ├── input/
│   └── output/
```

### script/ Directory
- **[create_crew.py](file:///d:/AI/crewAI/script/create_crew.py)**: Meta-agent system for generating crew configurations
- **[run_crew.py](file:///d:/AI/crewAI/script/run_crew.py)**: Execution engine that parses Markdown and runs crews
- **[tools_registry.py](file:///d:/AI/crewAI/script/tools_registry.py)**: Comprehensive tools management system
- **examples/**: Reference files for meta-agent generation
  - `Crew_Instruction.md`: Strict syntax rules for Crew.md parser
  - `Crew_Example.md`: Example crew configuration
  - `Task_Example.md`: Example task configuration with detailed description
  - `.env.example`: Example environment configuration

## Key Syntax Reference

### Crew.md Format
```markdown
# Crew Team: [Name]

## Configuration
- Architecture: sequential | hierarchical
- Supervisor Agent: [Name] | None

## Agents

### [Agent Name]
- **Role**: [Role description]
- **Goal**: [Agent's objective]
- **Backstory**: [Context and expertise]
- **Model**: [Optional: specific Ollama model]
- **Tools**: [Optional: FileReadTool, WebsiteSearchTool, etc.]

## Tasks

### [Task Name] [Output: custom_file.md]
- **Description**: [Task details with {task_input} or [[filename]] placeholders]
- **Expected Output**: [What the task should produce]
- **Agent**: [Agent Name]
```

### Task.md Format
```markdown
# User Task for Agents

[Enhanced, detailed task description with context, objectives, requirements, and quality standards]
```

### Placeholders
- `{task_input}`: Replaced with content from Task.md
- `[[filename]]`: Replaced with content from file (searches input/ first, then project root)
- `[Output: filename.md]`: Specifies custom output file for task results

## Workflow

### Creating a New Crew
1. Click **"+ New"** in the toolbar
2. Enter crew name and description
3. Click **"Generate Crew"** to describe your goal
4. Configure architecture options:
   - Choose Sequential or Hierarchical
   - Enable Supervisor for quality control
   - Enable Tool Agent for centralized external operations
   - Select models for agents and supervisor
5. Review generated agents and tasks
6. Use **"Refine Crew"** with feedback to iteratively improve
7. Click **"Save"** to persist changes

### Running a Crew
1. Select crew from dropdown
2. Ensure Task.md contains the detailed objective
3. Place any required files in the crew's `input/` directory
4. Click **"Run Crew"** to execute
5. Monitor progress in the execution log window
6. Review outputs in the crew's `output/` directory

### Iterative Refinement
1. Run crew and review outputs
2. Provide feedback in the "Refine Crew" dialog
3. System updates crew configuration based on feedback
4. Re-run and iterate until satisfied

## Architecture Modes

### Sequential Architecture
- Tasks execute in linear order: Task 1 → Task 2 → Task 3
- Each task completes before the next begins
- Agents work independently in sequence
- **Use when**: Steps depend on previous results

### Hierarchical Architecture
- Supervisor coordinates all work
- Supervisor reviews and approves outputs
- Workers execute under supervisor guidance
- **Use when**: Need central oversight and quality control

### Supervisor Mode (Optional)
- Add a supervisor agent with veto power
- Quality gates that output "APPROVED" or "REVISE: [reason]"
- Can use a stronger model for better judgment
- Does NOT create content, only evaluates and directs

### Tool Agent Mode (Optional)
- One agent handles ALL external operations
- Responsibilities: web search, file reading, data extraction
- Other agents REQUEST information from Tool Agent
- Benefits: No duplicate searches, consistent formatting, easier debugging

## Setup & Configuration

### Prerequisites
1. **Python 3.8+**: Required for running the application
2. **Ollama**: Local LLM server for running models
3. **Virtual Environment**: Recommended for dependency isolation

### Installation Steps
1. Install Ollama from [ollama.com](https://ollama.com/)
2. Pull required models: `ollama pull ministral-3:8b`
3. Create virtual environment: `python -m venv venv`
4. Activate environment:
   - Windows: `.\venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`

### Configuration
1. Launch GUI: `python app.py`
2. Open **Settings** menu
3. Configure:
   - `OLLAMA_SERVER`: Server address (default: localhost)
   - `OLLAMA_PORT`: Server port (default: 11434)
   - `OLLAMA_MODEL`: Default model (e.g., ministral-3:8b)
   - `OPENAI_API_KEY`: Optional for OpenAI tools
   - `OTEL_SDK_DISABLED`: Set to "true" to disable telemetry
   - `PYTHON_VENV_PATH`: Path to virtual environment (default: ./venv)

## Advanced Features

### File Sampling
Large files (>50KB) are automatically sampled to prevent context overflow:
- First 15KB (start of file)
- Middle 15KB (middle section)
- Last 15KB (end of file)

### Output Reuse
The system intelligently reuses previous outputs:
- Skip tasks if output already exists
- Inject existing outputs into dependent tasks
- Feedback loop for iterative improvement

### Custom Models per Agent
Assign different models to different agents:
- Use faster models for simple tasks
- Use stronger models for complex reasoning
- Use specialized models for specific domains

### Multi-Crew Workspace
Organize work into separate crews:
- Each crew has isolated configuration
- Switch between crews instantly
- Reuse successful crew patterns

## Troubleshooting

### Common Issues
1. **Model not found**: Ensure model is pulled in Ollama (`ollama list`)
2. **Connection refused**: Check Ollama server is running
3. **File not found**: Verify files are in crew's `input/` directory
4. **Empty output**: Check agent model compatibility and task descriptions

### Debug Tips
- Check execution logs for detailed error messages
- Verify Crew.md syntax matches examples
- Test with simple tasks first
- Use verbose mode for detailed agent reasoning

## Future Enhancements
See the "Proposed Improvements" section below for planned features and optimizations.
