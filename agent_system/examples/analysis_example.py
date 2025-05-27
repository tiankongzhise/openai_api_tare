import asyncio
from src.utils.factory import AgentFactory
from src.models.schemas import UserInput
from src.core.database import init_db # Import the async init_db function
from src.core.config import ConfigManager # To get DATABASE_URL
import os

async def main():
    # Load database URL from config or environment
    config_manager = ConfigManager()
    database_url = config_manager.database_url
    if not database_url:
        print("DATABASE_URL not found. Please set it in your environment or .env file.")
        print("Using default SQLite for example: sqlite+aiosqlite:///./analysis_example.db")
        database_url = "sqlite+aiosqlite:///./analysis_example.db"
        from dotenv import load_dotenv
        load_dotenv()
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./analysis_example.db")

    # Initialize database and create tables
    try:
        db_manager = await init_db(database_url) # init_db returns the DatabaseManager instance
        print(f"Database initialized with URL: {database_url}")
    except Exception as e:
        print(f"Error initializing database: {e}")
        print("Please ensure your DATABASE_URL is correctly configured for async operations (e.g., sqlite+aiosqlite:///./your.db)")
        return

    # 创建分析Agent
    analysis_agent = AgentFactory.create_agent("config/analysis_agent.toml")
    
    # 示例数据
    sample_data = """
    销售数据:
    1月: 100万
    2月: 120万
    3月: 95万
    4月: 150万
    5月: 180万
    """
    
    # 进行趋势分析
    request = UserInput(
        content=sample_data,
        data=sample_data,
        analysis_type="trend"
    )
    
    try:
        response = await analysis_agent.process(request)
        print("分析结果:")
        print(response.content)
        print(f"\n元数据: {response.metadata}")
        
    except Exception as e:
        print(f"分析失败: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
