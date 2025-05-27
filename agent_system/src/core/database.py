from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine as create_sync_engine, select, inspect as sqlalchemy_inspect, text
from sqlalchemy.schema import CreateTable
import sqlalchemy.schema # For AddConstraint, CreateIndex
from typing import List, Dict, Any, Type, Tuple
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError, OperationalError # OperationalError 通常用于网络问题
from datetime import datetime
import os
import asyncio
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_fixed

# 使用项目中统一的日志工具
from ..utils.logger import get_logger, LoggerConfig

# 获取一个logger实例，可以使用默认配置，或根据需要加载特定配置
# 例如，可以创建一个名为 'database' 的logger配置在 logger.toml 中
# logger = get_logger(LoggerConfig(name='database_logger', level='INFO')) # 日志记录器 = get_logger(LoggerConfig(名称='database_logger', 级别='INFO'))
# 或者简单使用默认配置，它会使用 logger.toml 中的 [logger.default]
logger = get_logger()

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
    def __init__(self, database_url: str, auto_sync_schema: bool = True):
        # 确保 database_url 适用于异步驱动，例如 postgresql+asyncpg
        # 如果原始 URL 是同步的，可能需要调整
        if not database_url.startswith("sqlite+aiosqlite") and "+" not in database_url.split("://")[1]:
            # 尝试为常见的数据库添加异步驱动
            if database_url.startswith("postgresql"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
            elif database_url.startswith("mysql"):
                database_url = database_url.replace("mysql://", "mysql+aiomysql://")
            # 对于 sqlite, 异步驱动是 aiosqlite
            elif database_url.startswith("sqlite"):
                 # 如果是相对路径，转换为绝对路径
                if database_url.startswith("sqlite:///") and not database_url.startswith("sqlite:///:"):
                    db_path = database_url.split("sqlite:///")[1]
                    if not os.path.isabs(db_path):
                        # 假设相对于项目根目录或特定已知目录
                        # 这里需要根据实际项目结构调整
                        # 为简单起见，我们假设它在项目根目录的 .db 文件
                        # database_url = f"sqlite+aiosqlite:///{os.path.abspath(db_path)}" # 数据库URL = f"sqlite+aiosqlite:///{os.path.abspath(db_path)}"
                        pass # 保持原样，让用户确保路径正确
                database_url = database_url.replace("sqlite", "sqlite+aiosqlite", 1)

        self.auto_sync_schema = auto_sync_schema
        self.async_engine = create_async_engine(database_url, echo=False) # echo=True 用于调试
        self.AsyncSessionLocal = sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def create_db_and_tables(self):
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        if self.auto_sync_schema:
            await self.compare_and_sync_schema(sync_db=True)

    async def compare_and_sync_schema(self, sync_db: bool = True):
        """比较ORM模型与数据库表结构，并根据需要同步。"""
        logger.info("开始比较ORM模式与数据库...")
        try:
            async with self.async_engine.connect() as conn:
                # 获取数据库中所有表的名称
                db_table_names = await conn.run_sync(
                    lambda sync_conn: sqlalchemy_inspect(sync_conn).get_table_names()
                )

                orm_tables = Base.metadata.tables
                mismatched_tables = set()

                for table_name, orm_table_obj in orm_tables.items():
                    if table_name not in db_table_names:
                        logger.warning(f"表 '{table_name}' 存在于ORM中但不存在于数据库中")
                        mismatched_tables.add(table_name)
                        continue
                    
                    # 比较列结构
                    try:
                        db_columns = await conn.run_sync(
                            lambda sync_conn: sqlalchemy_inspect(sync_conn).get_columns(table_name)
                        )
                        db_column_names = {col['name'] for col in db_columns}
                        orm_column_names = {col.name for col in orm_table_obj.columns}

                        # 检查列集合是否匹配
                        if db_column_names != orm_column_names:
                            logger.warning(f"表 '{table_name}' 的列集合不匹配")
                            logger.debug(f"数据库列: {db_column_names}, ORM列: {orm_column_names}")
                            mismatched_tables.add(table_name)
                        else:
                            # 列集合相同时，检查各列的详细属性
                            db_columns_dict = {col['name']: col for col in db_columns}
                            for orm_col_obj in orm_table_obj.columns:
                                orm_col_name = orm_col_obj.name
                                db_col_info = db_columns_dict.get(orm_col_name)

                                if not db_col_info:
                                    logger.warning(f"列 '{orm_col_name}' 在ORM中存在但在数据库表 '{table_name}' 中未找到")
                                    mismatched_tables.add(table_name)
                                    continue

                                # 检查列属性差异
                                column_mismatch_details = self._compare_column_attributes(
                                    orm_col_obj, db_col_info
                                )

                                if column_mismatch_details:
                                    logger.warning(f"表 '{table_name}', 列 '{orm_col_name}': 发现不匹配 - {'; '.join(column_mismatch_details)}")
                                    mismatched_tables.add(table_name)

                    except Exception as e_inspect_cols:
                        logger.error(f"检查表 {table_name} 的列时出错: {e_inspect_cols}")
                        mismatched_tables.add(table_name)

                    # 表级别约束比较
                    await self._compare_table_constraints(conn, table_name, orm_table_obj, mismatched_tables)

                # mismatched_tables 现在是一个集合
                if mismatched_tables:
                    logger.warning(f"Schema mismatch detected for tables: {list(mismatched_tables)}")
                    if sync_db:
                        logger.info(f"Attempting to sync schema by creating missing tables and altering existing ones...")
                        async with self.async_engine.begin() as conn_sync: # Outer transaction for create_all
                            # 1. Create entirely new tables defined in ORM but not in DB
                            logger.info("Step 1: Running Base.metadata.create_all to create missing tables.")
                            await conn_sync.run_sync(Base.metadata.create_all) 
                            logger.info("Step 1: Finished Base.metadata.create_all.")

                            # 2. For tables that exist but have mismatches, attempt to alter them
                            logger.info("Step 2: Attempting to alter existing tables with detected mismatches.")
                            for table_name in mismatched_tables: # Iterate over tables identified with issues
                                if table_name not in orm_tables: # Should not happen if mismatched_tables is populated correctly
                                    continue
                                orm_table_obj = orm_tables[table_name]
                                
                                # Re-fetch DB state for this specific table to be absolutely sure before altering
                                try:
                                    current_db_columns_info = await conn_sync.run_sync(
                                        lambda s_conn: sqlalchemy_inspect(s_conn).get_columns(table_name)
                                    )
                                    current_db_column_names = {c['name'] for c in current_db_columns_info}
                                    
                                    current_db_unique_constraints = await conn_sync.run_sync(
                                        lambda s_conn: sqlalchemy_inspect(s_conn).get_unique_constraints(table_name)
                                    )
                                    current_db_unique_constraints_set = {tuple(sorted(c['column_names'])) for c in current_db_unique_constraints}
                                    
                                    current_db_indexes = await conn_sync.run_sync(
                                        lambda s_conn: sqlalchemy_inspect(s_conn).get_indexes(table_name)
                                    )
                                    current_db_indexes_set = {tuple(sorted(idx['column_names'])) for idx in current_db_indexes}

                                except Exception as e_refetch:
                                    logger.error(f"Could not re-fetch schema for table {table_name} before alter: {e_refetch}. Skipping alterations for this table.")
                                    continue

                                # A. Add missing columns
                                for orm_col in orm_table_obj.columns:
                                    if orm_col.name not in current_db_column_names:
                                        try:
                                            # Note: This is a simplified ADD COLUMN. For full fidelity (defaults, constraints on column),
                                            # compiling the column object itself might be better, but more complex.
                                            # SQLAlchemy's DDL constructs are generally preferred over raw SQL.
                                            # However, a direct AddColumn DDL construct for a specific column isn't straightforward
                                            # without recompiling parts of the table. We'll use text for now for simplicity.
                                            # A more robust solution would use Alembic or deeper SQLAlchemy DDL compilation.
                                            col_type = orm_col.type.compile(self.async_engine.dialect)
                                            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {orm_col.name} {col_type}"
                                            if not orm_col.nullable:
                                                alter_sql += " NOT NULL"
                                            # Adding default values via ALTER is database-specific and complex here.
                                            # For simplicity, we'll skip adding defaults in this ALTER statement.
                                            # Consider `server_default` if it's critical.
                                            await conn_sync.execute(text(alter_sql))
                                            logger.info(f"Added column '{orm_col.name}' to table '{table_name}'.")
                                        except Exception as e_add_col:
                                            logger.error(f"Failed to add column '{orm_col.name}' to table '{table_name}': {e_add_col}")
                                    else:
                                        # Column exists, check for attribute mismatches to alter
                                        # Re-fetch the specific DB column info for detailed comparison if needed, or use from current_db_columns_info
                                        db_col_info_for_alter = next((c for c in current_db_columns_info if c['name'] == orm_col.name), None)
                                        if not db_col_info_for_alter: continue # Should not happen

                                        # B.1. Alter Column Type if mismatched
                                        orm_col_type_compiled = orm_col.type.compile(conn_sync.dialect)
                                        # db_col_info_for_alter['type'] is already a SQLAlchemy type object from inspect
                                        db_col_type_compiled = db_col_info_for_alter['type'].compile(conn_sync.dialect)

                                        _orm_type_class_name = type(orm_col.type).__name__.lower()
                                        _db_type_class_name = type(db_col_info_for_alter['type']).__name__.lower()
                                        
                                        is_compatible_for_alter = False
                                        # This compatibility check should mirror the one in the comparison phase
                                        if ((_orm_type_class_name == _db_type_class_name) or \
                                            ('int' in _orm_type_class_name and 'int' in _db_type_class_name) or \
                                            ('char' in _orm_type_class_name and 'char' in _db_type_class_name) or \
                                            ('text' in _orm_type_class_name and 'text' in _db_type_class_name) or \
                                            ('date' in _orm_type_class_name and 'date' in _db_type_class_name) or \
                                            ('time' in _orm_type_class_name and 'time' in _db_type_class_name) or \
                                            ('bool' in _orm_type_class_name and 'bool' in _db_type_class_name) or \
                                            ('num' in _orm_type_class_name and 'num' in _db_type_class_name) or \
                                            ('float' in _orm_type_class_name and 'float' in _db_type_class_name) or \
                                            ('lob' in _orm_type_class_name and 'lob' in _db_type_class_name)):
                                            is_compatible_for_alter = True

                                        if not is_compatible_for_alter and orm_col_type_compiled.lower() != db_col_type_compiled.lower():
                                            logger.info(f"Table '{table_name}', Column '{orm_col.name}': Type mismatch. ORM: '{orm_col_type_compiled}' (class: {_orm_type_class_name}), DB: '{db_col_type_compiled}' (class: {_db_type_class_name}). Attempting ALTER.")
                                            try:
                                                alter_type_sql = f"ALTER TABLE {table_name} ALTER COLUMN {orm_col.name} TYPE {orm_col_type_compiled}"
                                                using_clause = ""
                                                if conn_sync.dialect.name == 'postgresql':
                                                    # Heuristic for common PostgreSQL type conversions that require USING
                                                    db_type_is_textual = isinstance(db_col_info_for_alter['type'], (sqlalchemy.types.String, sqlalchemy.types.Text, sqlalchemy.types.Unicode, sqlalchemy.types.UnicodeText))
                                                    orm_type = orm_col.type
                                                    if db_type_is_textual:
                                                        if isinstance(orm_type, (sqlalchemy.types.Integer, sqlalchemy.types.BigInteger)):
                                                            using_clause = f" USING {orm_col.name}::INTEGER"
                                                        elif isinstance(orm_type, sqlalchemy.types.Numeric):
                                                            using_clause = f" USING {orm_col.name}::NUMERIC"
                                                        elif isinstance(orm_type, sqlalchemy.types.Boolean):
                                                            using_clause = f" USING {orm_col.name}::BOOLEAN"
                                                        elif isinstance(orm_type, sqlalchemy.types.Date):
                                                            using_clause = f" USING {orm_col.name}::DATE"
                                                        elif isinstance(orm_type, sqlalchemy.types.DateTime):
                                                            using_clause = f" USING {orm_col.name}::{'TIMESTAMP WITH TIME ZONE' if getattr(orm_type, 'timezone', False) else 'TIMESTAMP'}"
                                                        elif isinstance(orm_type, sqlalchemy.types.JSON):
                                                            using_clause = f" USING {orm_col.name}::JSONB" # or ::JSON depending on preference
                                                
                                                if using_clause:
                                                    alter_type_sql += using_clause
                                                
                                                await conn_sync.execute(text(alter_type_sql))
                                                logger.info(f"Table '{table_name}', Column '{orm_col.name}': Successfully altered type to '{orm_col_type_compiled}'.")
                                            except Exception as e_alter_type:
                                                logger.error(f"Table '{table_name}', Column '{orm_col.name}': Failed to alter type from '{db_col_type_compiled}' to '{orm_col_type_compiled}': {e_alter_type}. SQL: {alter_type_sql}")

                                        # B.2. Alter Nullable Constraint if mismatched
                                        orm_nullable = bool(orm_col.nullable)
                                        db_nullable = bool(db_col_info_for_alter['nullable'])
                                        if orm_nullable != db_nullable:
                                            logger.info(f"Table '{table_name}', Column '{orm_col.name}': Nullable mismatch. ORM: {orm_nullable}, DB: {db_nullable}. Attempting ALTER.")
                                            try:
                                                alter_nullable_sql = f"ALTER TABLE {table_name} ALTER COLUMN {orm_col.name} {'DROP NOT NULL' if orm_nullable else 'SET NOT NULL'}"
                                                await conn_sync.execute(text(alter_nullable_sql))
                                                logger.info(f"Table '{table_name}', Column '{orm_col.name}': Successfully altered NULLABLE to {orm_nullable}.")
                                            except Exception as e_alter_nullable:
                                                logger.error(f"Table '{table_name}', Column '{orm_col.name}': Failed to alter NULLABLE constraint: {e_alter_nullable}")
                                
                                # C. Add missing unique constraints
                                for constraint in orm_table_obj.constraints:
                                    if isinstance(constraint, sqlalchemy.UniqueConstraint):
                                        orm_uc_tuple = tuple(sorted(c.name for c in constraint.columns))
                                        if orm_uc_tuple not in current_db_unique_constraints_set:
                                            try:
                                                await conn_sync.execute(sqlalchemy.schema.AddConstraint(constraint))
                                                logger.info(f"Added unique constraint '{constraint.name}' on {orm_uc_tuple} to table '{table_name}'.")
                                            except Exception as e_add_uq:
                                                logger.error(f"Failed to add unique constraint '{constraint.name}' to table '{table_name}': {e_add_uq}")

                                # C. Add missing indexes
                                for index in orm_table_obj.indexes:
                                    orm_idx_tuple = tuple(sorted(c.name for c in index.columns))
                                    # Check if an index with the same columns already exists
                                    # This simple check doesn't consider index name or if it's unique from ORM vs DB.
                                    if orm_idx_tuple not in current_db_indexes_set:
                                        try:
                                            # Ensure the index is bound to the table if not already
                                            if index.table is None:
                                                index._set_parent(orm_table_obj) # Internal, but often necessary for CreateIndex
                                            await conn_sync.execute(sqlalchemy.schema.CreateIndex(index))
                                            logger.info(f"Added index '{index.name}' on {orm_idx_tuple} to table '{table_name}'.")
                                        except Exception as e_add_idx:
                                            logger.error(f"Failed to add index '{index.name}' to table '{table_name}': {e_add_idx}")
                        
                        logger.info("Schema sync attempt finished. Review database for actual changes and potential errors.")
                    else:
                        logger.info("Schema sync is disabled. Manual intervention may be required for mismatched tables.")
                else:
                    logger.info("ORM schema and database schema appear to be consistent (based on checks performed).")
                return not bool(mismatched_tables)
        except Exception as e:
            logger.error(f"Error during schema comparison/sync: {e}", exc_info=True)
            return False
    
    async def _compare_column_attributes(self, conn, table_name: str, orm_column, db_column_dict: dict, mismatched_tables: set):
        """比较ORM列与数据库列的属性"""
        column_name = orm_column.name
        
        if column_name not in db_column_dict:
            logger.warning(f"表 '{table_name}': 缺失列 '{column_name}'")
            mismatched_tables.add(table_name)
            return
        
        db_column = db_column_dict[column_name]
        
        # 比较列类型
        orm_type_str = str(orm_column.type).upper()
        db_type_str = str(db_column['type']).upper()
        
        if not self._are_types_compatible(orm_type_str, db_type_str):
            logger.warning(f"表 '{table_name}', 列 '{column_name}': 类型不匹配. ORM: {orm_type_str}, DB: {db_type_str}")
            mismatched_tables.add(table_name)
        
        # 比较可空性
        if orm_column.nullable != db_column['nullable']:
            logger.warning(f"表 '{table_name}', 列 '{column_name}': 可空性不匹配. ORM: {orm_column.nullable}, DB: {db_column['nullable']}")
            mismatched_tables.add(table_name)
        
        # 比较默认值（简化比较）
        orm_default = getattr(orm_column.default, 'arg', None) if orm_column.default else None
        db_default = db_column.get('default')
        if str(orm_default) != str(db_default):
            logger.warning(f"表 '{table_name}', 列 '{column_name}': 默认值不匹配. ORM: {orm_default}, DB: {db_default}")
            mismatched_tables.add(table_name)
    
    def _are_types_compatible(self, orm_type: str, db_type: str) -> bool:
        """检查ORM类型和数据库类型是否兼容"""
        if orm_type == db_type:
            return True
        
        # 类型映射表
        type_mappings = {
            'INTEGER': ['INT', 'INT4', 'SERIAL'],
            'VARCHAR': ['TEXT', 'CHARACTER VARYING', 'CHAR'],
            'BOOLEAN': ['BOOL'],
            'TIMESTAMP': ['DATETIME'],
            'FLOAT': ['REAL', 'DOUBLE PRECISION'],
            'TEXT': ['VARCHAR', 'CHARACTER VARYING']
        }
        
        for orm_base_type, db_equivalents in type_mappings.items():
            if orm_base_type in orm_type:
                return any(db_equiv in db_type for db_equiv in db_equivalents)
        
        return False
    
    async def _compare_table_constraints(self, conn, table_name: str, orm_table_obj, mismatched_tables: set):
        """比较表级别约束（主键、唯一约束、索引）"""
        try:
            # 比较主键
            db_pk_constraint = await conn.run_sync(
                lambda sync_conn: sqlalchemy_inspect(sync_conn).get_pk_constraint(table_name)
            )
            orm_pk_columns = {col.name for col in orm_table_obj.primary_key.columns}
            db_pk_columns = set(db_pk_constraint.get('constrained_columns', []))
            if orm_pk_columns != db_pk_columns:
                logger.warning(f"表 '{table_name}': 主键不匹配. ORM: {orm_pk_columns}, DB: {db_pk_columns}")
                mismatched_tables.add(table_name)
        except Exception as e:
            logger.error(f"比较表 {table_name} 主键时出错: {e}")
            mismatched_tables.add(table_name)
        
        try:
            # 比较唯一约束
            db_unique_constraints = await conn.run_sync(
                lambda sync_conn: sqlalchemy_inspect(sync_conn).get_unique_constraints(table_name)
            )
            orm_unique_constraints = set()
            for constraint in orm_table_obj.constraints:
                if isinstance(constraint, sqlalchemy.UniqueConstraint):
                    orm_unique_constraints.add(tuple(sorted(col.name for col in constraint.columns)))
            
            db_unique_constraints_set = set()
            for const in db_unique_constraints:
                db_unique_constraints_set.add(tuple(sorted(const['column_names'])))

            if orm_unique_constraints != db_unique_constraints_set:
                logger.warning(f"表 '{table_name}': 唯一约束不匹配. ORM: {orm_unique_constraints}, DB: {db_unique_constraints_set}")
                mismatched_tables.add(table_name)
        except Exception as e:
            logger.error(f"比较表 {table_name} 唯一约束时出错: {e}")
            mismatched_tables.add(table_name)
        
        try:
            # 比较索引
            db_indexes = await conn.run_sync(
                lambda sync_conn: sqlalchemy_inspect(sync_conn).get_indexes(table_name)
            )
            orm_indexes_set = set()
            for index in orm_table_obj.indexes:
                orm_indexes_set.add(tuple(sorted(col.name for col in index.columns)))

            db_indexes_info_set = set()
            for idx in db_indexes:
                db_indexes_info_set.add(tuple(sorted(idx['column_names'])))

            if orm_indexes_set != db_indexes_info_set:
                logger.warning(f"表 '{table_name}': 索引不匹配. ORM: {orm_indexes_set}, DB: {db_indexes_info_set}")
                mismatched_tables.add(table_name)
        except Exception as e:
            logger.error(f"比较表 {table_name} 索引时出错: {e}")
            mismatched_tables.add(table_name)

    async def get_unique_constraints(self, table_name: str) -> List[Tuple[str, ...]]:
        """查找表的全部唯一索引组 (包括主键和唯一约束)。"""
        unique_constraints_list = []
        try:
            async with self.async_engine.connect() as conn:
                # 获取主键约束
                pk_constraint = await conn.run_sync(
                    lambda sync_conn: sqlalchemy_inspect(sync_conn).get_pk_constraint(table_name)
                )
                if pk_constraint and pk_constraint.get('constrained_columns'):
                    unique_constraints_list.append(tuple(sorted(pk_constraint['constrained_columns'])))

                # 获取唯一约束
                unique_db_constraints = await conn.run_sync(
                    lambda sync_conn: sqlalchemy_inspect(sync_conn).get_unique_constraints(table_name)
                )
                for constraint in unique_db_constraints:
                    if constraint.get('column_names'):
                        unique_constraints_list.append(tuple(sorted(constraint['column_names'])))
                
                # 获取索引，并筛选出唯一索引
                indexes = await conn.run_sync(
                    lambda sync_conn: sqlalchemy_inspect(sync_conn).get_indexes(table_name)
                )
                for index in indexes:
                    if index.get('unique'):
                        cols = tuple(sorted(index['column_names']))
                        if cols not in unique_constraints_list: # 避免重复添加 (例如主键可能也有独立的索引)
                             unique_constraints_list.append(cols)

            # 去重，因为不同方法获取的约束可能重叠
            if unique_constraints_list:
                unique_constraints_list = sorted(list(set(unique_constraints_list)))
            logger.info(f"Unique constraints for table '{table_name}': {unique_constraints_list}")
            return unique_constraints_list
        except Exception as e:
            logger.error(f"Error getting unique constraints for table '{table_name}': {e}", exc_info=True)
            return []

    async def filter_new_data(self, table_class: Type[Base], data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """根据输入的数据和唯一索引组，筛选出不在数据库中的数据。"""
        if not data_list:
            return []

        table_name = table_class.__tablename__
        unique_constraints = await self.get_unique_constraints(table_name)
        new_data = []

        if not unique_constraints:
            logger.warning(f"No unique constraints found for table '{table_name}'. Cannot reliably filter new data. Returning all data.")
            # 在没有唯一约束的情况下，无法有效判断数据是否“新”。
            # 可以选择返回所有数据，或抛出错误，或基于主键（如果存在）进行简单检查。
            # 这里为了安全，暂时返回所有数据，但实际应用中应有更明确的策略。
            return data_list

        async with self.get_session() as session:
            for item_data in data_list:
                is_existing = False
                for constraint_columns in unique_constraints:
                    # 确保所有约束列都在item_data中
                    if not all(col_name in item_data for col_name in constraint_columns):
                        # logger.debug(f"由于缺少键，跳过项 {item_data} 的约束 {constraint_columns}。")
                        continue # 如果数据项缺少唯一约束的某个键，则无法用此约束判断
                    
                    filters = [getattr(table_class, col) == item_data[col] for col in constraint_columns]
                    query = select(table_class).filter(*filters)
                    result = await session.execute(select(query.exists()))
                    if result.scalar_one_or_none():
                        is_existing = True
                        # logger.debug(f"数据项 {item_data} 通过约束 {constraint_columns} 在数据库中找到已存在。")
                        break # 找到一个匹配的约束就说明数据已存在
                
                if not is_existing:
                    new_data.append(item_data)
        
        logger.info(f"Filtered {len(data_list) - len(new_data)} existing items. Returning {len(new_data)} new items for table '{table_name}'.")
        return new_data

    
    async def get_session(self) -> AsyncSession:
        return self.AsyncSessionLocal()
    
    @retry(stop=stop_after_attempt(3), 
           retry=retry_if_exception_type(OperationalError), # 仅在 OperationalError (通常是网络/连接问题) 时重试
           wait=wait_fixed(1), # 每次重试等待1秒
           reraise=True) # 如果重试后仍然失败，则重新抛出异常
    async def save_conversation(
        self,
        agent_type: str,
        user_input: str,
        agent_response: str,
        session_id: str = None,
        conversation_data: dict = None # 用于记录失败数据
    ):
        """异步保存对话历史，带有重试机制"""
        if conversation_data is None:
            conversation_data = {
                "agent_type": agent_type,
                "user_input": user_input,
                "agent_response": agent_response,
                "session_id": session_id
            }

        try:
            async with self.get_session() as session:
                async with session.begin(): # 使用事务块
                    conversation = ConversationHistory(
                        agent_type=agent_type,
                        user_input=user_input,
                        agent_response=agent_response,
                        session_id=session_id
                    )
                    session.add(conversation)
                    await session.commit()
                logger.info(f"Conversation saved successfully for session_id: {session_id}")
        except IntegrityError as e:
            # 事务性错误，如重复输入 (唯一约束冲突)
            logger.error(f"IntegrityError while saving conversation: {e}. Data: {conversation_data}")
            # 不进行重试，直接失败并记录
            # 可以选择抛出自定义异常或返回特定错误码
            raise # 或者返回 False，或根据应用程序逻辑处理
        except OperationalError as e:
            # 网络波动或数据库连接问题，tenacity 会处理重试
            logger.warning(f"OperationalError (retrying...): {e}. Data: {conversation_data}")
            raise # 重新引发异常以便 tenacity 处理重试
        except Exception as e:
            # 其他未知错误
            logger.error(f"Unexpected error while saving conversation: {e}. Data: {conversation_data}")
            # 记录失败数据
            # 对于其他未知错误，也可能需要根据情况决定是否重试，但当前配置仅重试 OperationalError
            raise # 或者返回 False，或根据应用程序逻辑处理
    
    async def get_conversation_history(
        self,
        agent_type: str,
        session_id: str = None,
        limit: int = 10
    ):
        """异步获取对话历史"""
        try:
            async with self.get_session() as session:
                query = select(ConversationHistory).filter(
                    ConversationHistory.agent_type == agent_type
                )
                if session_id:
                    query = query.filter(ConversationHistory.session_id == session_id)
                
                result = await session.execute(
                    query.order_by(ConversationHistory.timestamp.desc()).limit(limit)
                )
                return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}", exc_info=True)
            return [] # 或者根据需要抛出异常

# 示例：初始化和建表 (通常在应用启动时执行一次)
async def init_db(database_url: str):
    db_manager = DatabaseManager(database_url)
    await db_manager.create_db_and_tables()
    return db_manager

# 如果直接运行此文件，可以添加一个简单的异步主函数来测试
# async def main(): # 异步主函数
#     # 从环境变量或配置文件获取 DATABASE_URL
#     # 注意：SQLite 的异步 URL 应该是 sqlite+aiosqlite:///./your_database.db
#     DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test_async.db") # 数据库URL = os.getenv("数据库URL", "sqlite+aiosqlite:///./test_async.db")
#     db_manager = await init_db(DATABASE_URL)
# 
#     # 测试保存
#     try: # 尝试
#         await db_manager.save_conversation( # 等待数据库管理器保存对话
#             agent_type="test_agent", # 代理类型="测试代理"
#             user_input="hello_async", # 用户输入="你好异步"
#             agent_response="world_async" # 代理响应="世界异步"
#         )
#         print("测试对话已保存。")
#     except Exception as e: # 捕获异常 e
#         print(f"保存测试对话时出错：{e}")
# 
#     # 测试获取
#     history = await db_manager.get_conversation_history(agent_type="test_agent", limit=5) # 历史 = 等待数据库管理器获取对话历史(代理类型="测试代理", 限制=5)
#     print("对话历史：")
#     for item in history: # 对于历史中的每一项
#         print(f"- {item.user_input} -> {item.agent_response} ({item.timestamp})") # 打印(f"- {项.用户输入} -> {项.代理响应} ({项.时间戳})")
# 
# if __name__ == "__main__": # 如果名称等于 "__main__"
#     asyncio.run(main()) # 异步运行(主函数)
