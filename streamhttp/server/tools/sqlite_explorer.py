from pathlib import Path
import sqlite3
import os
from typing import List, Dict, Any, Optional
from loguru import logger

from server import mcp

if 'SQLITE_DB_PATH' not in os.environ:
    os.environ["SQLITE_DB_PATH"] = "./data/sqlite.db"

# Setup logging
logger.add("sqlite_explorer_debug.log", level="DEBUG", rotation="1 MB")

DB_PATH = Path(os.environ['SQLITE_DB_PATH'])
print(f"SQLiteExplorer tools Using database path: {DB_PATH}")
if not DB_PATH.is_file():
    raise FileNotFoundError(f"Database file not found at {DB_PATH}")
logger.debug(f"Using database path: {DB_PATH}")


class SQLiteConnection:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        logger.debug(f"Opened SQLite connection to: {self.db_path}")
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
            logger.debug("Closed SQLite connection")

def contains_multiple_statements(sql: str) -> bool:
    in_single_quote = False
    in_double_quote = False
    for char in sql:
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif char == ';' and not in_single_quote and not in_double_quote:
            return True
    return False


@mcp.tool()
def read_query(query: str, 
               params: Optional[List[Any]] = None, fetch_all: bool = True, 
               row_limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Run a SELECT query on the SQLite database.

    Use this tool to execute SQL queries that read data from the database. 
    Only SELECT or WITH queries are allowed. 
    You can use it to preview table contents, filter rows, or perform aggregates.
    
    Args:
        query: The SELECT SQL query string to execute.
        params: Optional query parameters.
        fetch_all: Whether to return all rows or just the first row.
        row_limit: Limit the number of returned rows (defaults to 1000).
    """

    logger.debug(f"Executing query: {query} with params: {params} (fetch_all={fetch_all}, row_limit={row_limit})")
   

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Messages database not found at: {DB_PATH}")
    query = query.strip().rstrip(';')
    if contains_multiple_statements(query):
        raise ValueError("Multiple SQL statements are not allowed")
    
    if not query.lower().startswith(('select', 'with')):
        raise ValueError("Only SELECT queries (or WITH) are allowed")

    logger.debug(f"Processed query: {query}")
    params = params or []
    with SQLiteConnection(DB_PATH) as conn:
        logger.debug(f"Using database connection: {conn}")
        cursor = conn.cursor()
        try:
            if 'limit' not in query.lower():
                query = f"{query} LIMIT {row_limit}"
            logger.debug(f"Final SQL: {query}")
            cursor.execute(query, params)
            results = cursor.fetchall() if fetch_all else [cursor.fetchone()]
            logger.debug(f"Fetched {len(results)} rows")
            return [dict(row) for row in results if row is not None]
        except sqlite3.Error as e:
            logger.exception("SQLite error occurred")
            raise ValueError(f"SQLite error: {str(e)}")
        
@mcp.tool()
def list_tables() -> List[str]:
    """
    List all tables in the SQLite database.

    Use this tool to retrieve the names of all tables in the database. 
    This is useful before attempting to read or describe a table.
    """
    logger.debug("Listing all tables in the database")


    if not DB_PATH.exists():
        raise FileNotFoundError(f"Messages database not found at: {DB_PATH}")
    with SQLiteConnection(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            tables = [row['name'] for row in cursor.fetchall()]
            logger.debug(f"Tables found: {tables}")
            return tables
        except sqlite3.Error as e:
            logger.exception("SQLite error while listing tables")
            raise ValueError(f"SQLite error: {str(e)}")

@mcp.tool()
def describe_table(table_name: str) -> List[Dict[str, str]]:
    """
    Describe a table's schema.

    Use this tool to get information about the columns in a specific table, including 
    column name, data type, nullability, and default values.
    
    Args:
        table_name: The name of the table to describe.
    """
    logger.debug(f"Describing table: {table_name}")


    if not DB_PATH.exists():
        raise FileNotFoundError(f"Messages database not found at: {DB_PATH}")
    with SQLiteConnection(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [table_name])
            if not cursor.fetchone():
                raise ValueError(f"Table '{table_name}' does not exist")

            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            # Convert all values to strings to satisfy Pydantic constraints
            schema = [{k: str(v) if v is not None else "" for k, v in dict(row).items()} for row in columns]
            logger.debug(f"Schema for table {table_name}: {schema}")
            return schema
        except sqlite3.Error as e:
            logger.exception("SQLite error while describing table")
            raise ValueError(f"SQLite error: {str(e)}")
    
