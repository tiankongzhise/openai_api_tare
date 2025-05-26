import asyncio
from src.utils.factory import AgentFactory
from src.models.schemas import UserInput

async def main():
    # 创建聊天Agent
    chat_agent = AgentFactory.create_agent("config/chat_agent.toml")
    
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