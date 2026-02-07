import os
import re
import json
from dotenv import load_dotenv, find_dotenv

class CrewModel:
    def __init__(self):
        self.agents = []
        self.tasks = []
        self.crews_dir = "crews"
        self.current_crew_name = "default"
        self.current_crew_path = os.path.join(self.crews_dir, "default")
        self.crew_file = os.path.join(self.current_crew_path, "Crew.md")
        self.task_file = os.path.join(self.current_crew_path, "Task.md")
        
        # Ensure crews dir exists
        if not os.path.exists(self.crews_dir):
            os.makedirs(self.crews_dir)

    def get_crews(self):
        crews = []
        if os.path.exists(self.crews_dir):
            for item in os.listdir(self.crews_dir):
                path = os.path.join(self.crews_dir, item)
                if os.path.isdir(path):
                    crews.append(item)
        return sorted(crews)

    def set_active_crew(self, crew_name):
        self.current_crew_name = crew_name
        self.current_crew_path = os.path.join(self.crews_dir, crew_name)
        self.crew_file = os.path.join(self.current_crew_path, "Crew.md")
        self.task_file = os.path.join(self.current_crew_path, "Task.md")
        # Ensure input folder exists for older crews
        input_dir = os.path.join(self.current_crew_path, "input")
        if not os.path.exists(input_dir):
            try:
                os.makedirs(input_dir)
            except: pass
        self.load_data()

    def create_new_crew(self, name, description):
        folder_name = "".join(x for x in name if x.isalnum() or x in "._- ")
        folder_path = os.path.join(self.crews_dir, folder_name)
        
        if os.path.exists(folder_path):
            return False, "Crew already exists"
            
        try:
            os.makedirs(folder_path)
            os.makedirs(os.path.join(folder_path, "output"))
            os.makedirs(os.path.join(folder_path, "input"))
            
            # Create json info
            info = {
                "name": name,
                "description": description,
                "folder": folder_name
            }
            with open(os.path.join(folder_path, "crew.json"), 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=4)
                
            # Create empty placeholder files
            with open(os.path.join(folder_path, "Crew.md"), 'w', encoding='utf-8') as f:
                f.write(f"# Crew Team: {name}\n\n## Agents\n\n## Tasks\n")
            
            with open(os.path.join(folder_path, "Task.md"), 'w', encoding='utf-8') as f:
                f.write(f"# User Task for Agents\n\n{description}\n")

            return True, folder_name
        except Exception as e:
            return False, str(e)

    def rename_crew(self, current_name, new_name):
        new_folder_name = "".join(x for x in new_name if x.isalnum() or x in "._- ")
        if not new_folder_name:
            return False, "Invalid name"
            
        current_path = os.path.join(self.crews_dir, current_name)
        new_path = os.path.join(self.crews_dir, new_folder_name)
        
        if os.path.exists(new_path):
             return False, "Crew name/folder already exists"
        
        try:
            os.rename(current_path, new_path)
            
            # Update crew.json
            json_path = os.path.join(new_path, "crew.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                data['name'] = new_name
                data['folder'] = new_folder_name
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
            
            # Update internal state if this was active
            if self.current_crew_name == current_name:
                self.set_active_crew(new_folder_name)
                
            return True, new_folder_name
        except Exception as e:
            return False, str(e)

    def load_data(self):
        self.agents = []
        self.tasks = []
        self.load_crew()
        self.load_task()

    def load_crew(self):
        if not os.path.exists(self.crew_file):
            return

        try:
            with open(self.crew_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse Agents
            agents_part_match = re.search(r"## Agents(.*?)(## Tasks|$)", content, re.DOTALL)
            if agents_part_match:
                agents_str = agents_part_match.group(1)
                agent_matches = re.finditer(r"### (.*?)\n(.*?)(?=### |$)", agents_str, re.DOTALL)
                for m in agent_matches:
                    name = m.group(1).strip()
                    details = m.group(2)
                    
                    def find_d(p, t):
                        m = re.search(p, t)
                        return m.group(1).strip() if m else ""

                    self.agents.append({
                        'name': name,
                        'role': find_d(r"\*\*\s*Role\s*\*\*: (.*)", details),
                        'goal': find_d(r"\*\*\s*Goal\s*\*\*: (.*)", details),
                        'backstory': find_d(r"\*\*\s*Backstory\s*\*\*: (.*)", details),
                        'model': find_d(r"\*\*\s*Model\s*\*\*: (.*)", details),
                        'web_search': "brave_search" in find_d(r"\*\*\s*Tools\s*\*\*: (.*)", details)
                    })

            # Parse Tasks
            tasks_part_match = re.search(r"## Tasks(.*)", content, re.DOTALL)
            if tasks_part_match:
                tasks_str = tasks_part_match.group(1)
                task_matches = re.finditer(r"### (.*?)\n(.*?)(?=### |$)", tasks_str, re.DOTALL)
                for m in task_matches:
                    title_line = m.group(1).strip()
                    output_file = ""
                    name = title_line
                    out_m = re.search(r"\[Output: (.*?)\]", title_line)
                    if out_m:
                        output_file = out_m.group(1).strip()
                        name = re.sub(r"\[Output: .*?\]", "", title_line).strip()
                    
                    details = m.group(2)
                    def find_d(p, t):
                        m = re.search(p, t)
                        return m.group(1).strip() if m else ""

                    self.tasks.append({
                        'name': name,
                        'output_file': output_file,
                        'description': find_d(r"\*\*\s*Description\s*\*\*: (.*)", details),
                        'expected_output': find_d(r"\*\*\s*Expected Output\s*\*\*: (.*)", details),
                        'agent': find_d(r"\*\*\s*Agent\s*\*\*: (.*)", details)
                    })
        except Exception as e:
            print(f"Error loading crew file: {e}")

    def load_task(self):
        if not os.path.exists(self.task_file):
            return ""
        
        try:
            with open(self.task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            content = re.sub(r"^\s*# User Task for Agents\s*\n*", "", content, flags=re.IGNORECASE | re.MULTILINE).strip()
            return content
        except Exception as e:
            print(f"Error loading task file: {e}")
            return ""

    def save_data(self, agents_data, tasks_data, user_task_content):
        try:
            # Crew
            crew_output = f"# Crew Team: {self.current_crew_name}\n\n## Agents\n\n"
            for a in agents_data:
                if not a['name']: continue
                crew_output += f"### {a['name']}\n"
                crew_output += f"- **Role**: {a['role']}\n"
                crew_output += f"- **Goal**: {a['goal']}\n"
                crew_output += f"- **Backstory**: {a['backstory']}\n"
                crew_output += f"- **Model**: {a['model']}\n"
                if a.get('web_search'):
                    crew_output += f"- **Tools**: brave_search\n"
                crew_output += "\n"
            
            crew_output += "## Tasks\n\n"
            for t in tasks_data:
                if not t['name']: continue
                out_part = f" [Output: {t['output_file']}]" if t['output_file'] else ""
                crew_output += f"### {t['name']}{out_part}\n"
                crew_output += f"- **Description**: {t['description']}\n"
                crew_output += f"- **Expected Output**: {t['expected_output']}\n"
                crew_output += f"- **Agent**: {t['agent']}\n\n"
            
            with open(self.crew_file, 'w', encoding='utf-8') as f:
                f.write(crew_output)

            # Task
            with open(self.task_file, 'w', encoding='utf-8') as f:
                f.write("# User Task for Agents\n\n" + user_task_content + "\n")
            
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False