import asyncio
from src.utils.factory import AgentFactory
from src.models.schemas import UserInput

async def main():
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