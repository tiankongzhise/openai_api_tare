import asyncio
from src.utils.factory import AgentFactory
from src.models.schemas import UserInput
from src.core.database import init_db # Import the async init_db function
from src.core.config import ConfigManager # To get DATABASE_URL
import os

async def main():
    # Load database URL from config or environment
    # This assumes DATABASE_URL is set in .env or environment variables
    # and accessible via ConfigManager or directly via os.getenv
    config_manager = ConfigManager()
    database_url = config_manager.database_url
    if not database_url:
        # Fallback or error if DATABASE_URL is not found
        print("DATABASE_URL not found. Please set it in your environment or .env file.")
        print("Using default SQLite for example: sqlite+aiosqlite:///./chat_example.db")
        database_url = "sqlite+aiosqlite:///./chat_example.db"
        # Ensure the .env file is loaded if you expect it to be
        from dotenv import load_dotenv
        load_dotenv() # Load .env if present
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chat_example.db")


    # Initialize database and create tables
    # This should ideally be done once at application startup.
    try:
        db_manager = await init_db(database_url) # init_db returns the DatabaseManager instance
        print(f"Database initialized with URL: {database_url}")
    except Exception as e:
        print(f"Error initializing database: {e}")
        print("Please ensure your DATABASE_URL is correctly configured for async operations (e.g., sqlite+aiosqlite:///./your.db)")
        return

    # 创建聊天Agent
    # AgentFactory.create_agent is synchronous and returns an agent instance.
    # The agent's __init__ method, which sets up db_manager, is also synchronous.
    # The db_manager instance within the agent will use the async engine configured by init_db.
    chat_agent = AgentFactory.create_agent("config/chat_agent.toml")
    # It's important that the agent uses the *same* database_url that was used for init_db.
    # The current BaseAgent.__init__ re-initializes DatabaseManager. This could be a point of refactoring
    # to pass an already initialized db_manager, but for now, we ensure the URL is consistent.
    # We can assign the initialized db_manager to the agent if the factory/agent design allows for it.
    # For simplicity here, we rely on the agent re-initializing with the same URL.
    # A better approach would be to pass the db_manager instance to the agent or factory.
    # chat_agent.db_manager = db_manager # If agent design allows direct assignment
    
    print("聊天Agent已启动，输入'quit'退出")
    
    while True:
        user_input = input("\n用户: ")
        if user_input.lower() == 'quit':
            break
        
        try:
            # 处理用户输入
            request = UserInput(content=user_input)
            response = await chat_agent.process(request)
            
            print(f"助手: {response.content}")
            
        except Exception as e:
            print(f"错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
