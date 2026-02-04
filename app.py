"""
CrewAI GUI Application
Main entry point for the application.
This is a compatibility wrapper that imports from the new app module structure.
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

if __name__ == "__main__":
    from app.main import main
    main()