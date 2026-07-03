"""Database helper module for SQLite integration.

Provides connection management and SQL query execution helper functions.
"""

from __future__ import annotations
import sqlite3
import uuid
import json
import logging
import os
from config import DB_PATH

logger = logging.getLogger(__name__)

def get_connection() -> sqlite3.Connection:
    """Establish and return a configured SQLite connection.
    
    The connection is configured with row_factory set to sqlite3.Row
    and foreign key constraints enabled.
    """
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection

def initialize_db() -> None:
    """Initialize the database by executing schema.sql if not already done."""
    try:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        if not os.path.exists(schema_path):
            logger.error(f"schema.sql not found at {schema_path}")
            return
            
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            
        conn = get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
            logger.info("Database schema initialized.")
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT query and return a list of dictionaries."""
    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Database fetch_all error for '{query}': {e}")
        return []

def fetch_one(query: str, params: tuple = ()) -> dict | None:
    """Execute a SELECT query and return a single row dictionary or None."""
    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Database fetch_one error for '{query}': {e}")
        return None

def get_pk_name(table: str) -> str:
    """Get the primary key field name based on table naming patterns."""
    if table == "compliance_events":
        return "event_id"
    if table == "audit_logs":
        return "log_id"
    if table == "inventory":
        return "inventory_id"
    if table == "risk_scores":
        return "score_id"
    if table.endswith("s"):
        return f"{table[:-1]}_id"
    return f"{table}_id"

def insert_row(table: str, data: dict) -> str:
    """Insert a single row of data into a table and return the primary key value.
    
    Automatically generates UUID if the primary key field is absent or empty.
    Serializes list or dictionary fields to JSON strings.
    """
    pk_name = get_pk_name(table)
    row_data = dict(data)
    
    if pk_name not in row_data or not row_data[pk_name]:
        row_data[pk_name] = str(uuid.uuid4())
        
    columns = list(row_data.keys())
    placeholders = []
    values = []
    
    for col in columns:
        val = row_data[col]
        if isinstance(val, (dict, list)):
            val = json.dumps(val)
        elif isinstance(val, bool):
            val = 1 if val else 0
        values.append(val)
        placeholders.append("?")
        
    query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
    
    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return row_data[pk_name]
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Database insert_row error for table '{table}': {e}")
        raise

def execute_query(query: str, params: tuple = ()) -> None:
    """Execute a non-SELECT query (such as INSERT, UPDATE, DELETE)."""
    try:
        conn = get_connection()
        try:
            conn.execute(query, params)
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Database execute_query error for '{query}': {e}")
        raise
