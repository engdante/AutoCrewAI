# CrewAI GUI & Automation System

## Project Description
This project represents an advanced system for managing and automating CrewAI agent teams. It provides a graphical user interface (GUI) that allows for easy definition of agents and tasks, as well as automatic generation of configuration files (`Crew.md` and `Task.md`) using meta-agents.

The system is designed to facilitate the creation of AI workflows by providing tools for:
- Managing agent roles and goals.
- Defining tasks and routing results.
- Dynamically loading context from files.
- Executing teams via a user-friendly interface.

## Installation and Setup

Follow the steps below to install and run the project.

### 1. Install Ollama
This project relies on Ollama for running local LLM models.
1. Download and install Ollama from the [official website](https://ollama.com/).
2. Start the Ollama server.
3. Pull the necessary models (e.g., `ministral-3:8b` or others you plan to use):
   ```bash
   ollama pull ministral-3:8b
   ```

### 2. Create a Virtual Environment (venv)
It is recommended to use a virtual environment to isolate project dependencies.

Open a terminal in the project's root directory and run:

```bash
python -m venv venv
```

### 3. Activate the Environment
Activate the created virtual environment:

- **Windows:**
  ```powershell
  .\venv\Scripts\activate
  ```

- **Linux / macOS:**
  ```bash
  source venv/bin/activate
  ```

### 4. Install Dependencies (start requirements.txt)
Install the necessary Python libraries listed in the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Running the Application

Once you have completed all installation steps, you can start the graphical interface:

```bash
python app.py
```

This will open the application window where you can manage your CrewAI teams.
