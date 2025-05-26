from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True)
    agent_type = Column(String(50), nullable=False)
    user_input = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String(100))

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        return self.SessionLocal()
    
    def save_conversation(
        self,
        agent_type: str,
        user_input: str,
        agent_response: str,
        session_id: str = None
    ):
        """保存对话历史"""
        with self.get_session() as session:
            conversation = ConversationHistory(
                agent_type=agent_type,
                user_input=user_input,
                agent_response=agent_response,
                session_id=session_id
            )
            session.add(conversation)
            session.commit()
    
    def get_conversation_history(
        self,
        agent_type: str,
        session_id: str = None,
        limit: int = 10
    ) -> List[ConversationHistory]:
        """获取对话历史"""
        with self.get_session() as session:
            query = session.query(ConversationHistory).filter(
                ConversationHistory.agent_type == agent_type
            )
            if session_id:
                query = query.filter(ConversationHistory.session_id == session_id)
            
            return query.order_by(
                ConversationHistory.timestamp.desc()
            ).limit(limit).all()