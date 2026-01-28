"""Database service endpoints for querying PostgreSQL metadata and data"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from models import ShpblResponse

router = APIRouter(prefix="/db", tags=["database"])


class GetTablesRequest(BaseModel):
    """Request model for getting tables in a schema"""

    schema_name: str = Field(..., description="Schema name to query tables from")


class GetTableDataRequest(BaseModel):
    """Request model for getting data from a table"""

    schema_name: str = Field(..., description="Schema name")
    table_name: str = Field(..., description="Table name")
    limit: int = Field(
        100, ge=1, le=1000, description="Maximum number of rows to return (1-1000)"
    )
    offset: int = Field(0, ge=0, description="Number of rows to skip")


@contextmanager
def get_db_connection():
    """
    Context manager for database connections

    Yields:
        psycopg2 connection object
    """
    conn = None
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "db"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "postgres"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
        )
        yield conn
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=500, detail=f"Database connection error: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


@router.get("/schemas", response_model=ShpblResponse)
async def get_schemas():
    """
    Get all database schemas

    Returns list of schema names excluding system schemas (pg_*, information_schema)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name NOT LIKE 'pg_%' 
                      AND schema_name != 'information_schema'
                    ORDER BY schema_name
                """
                )
                schemas = [row[0] for row in cur.fetchall()]

        return ShpblResponse(
            success=True,
            message=f"Found {len(schemas)} schema(s)",
            data={"schemas": schemas},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to query schemas: {str(e)}"
        )


@router.get("/tables", response_model=ShpblResponse)
async def get_tables(schema_name: str = Query(..., description="Schema name to query")):
    """
    Get all tables in a specific schema with row counts

    Args:
        schema_name: Name of the schema to query

    Returns:
        List of tables with their row counts
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Verify schema exists
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s",
                    (schema_name,),
                )
                if cur.fetchone()[0] == 0:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Schema '{schema_name}' does not exist. Please check the schema name and try again.",
                    )

                # Get tables in the schema
                cur.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = %s 
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """,
                    (schema_name,),
                )

                table_names = [row[0] for row in cur.fetchall()]

                # Get row counts for each table
                tables_data = []
                for table_name in table_names:
                    cur.execute(f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"')
                    row_count = cur.fetchone()[0]
                    tables_data.append(
                        {"table_name": table_name, "row_count": row_count}
                    )

        return ShpblResponse(
            success=True,
            message=f"Found {len(tables_data)} table(s) in schema '{schema_name}'",
            data={"tables": tables_data},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query tables: {str(e)}")


@router.get("/table-data", response_model=ShpblResponse)
async def get_table_data(
    schema_name: str = Query(..., description="Schema name"),
    table_name: str = Query(..., description="Table name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
):
    """
    Get data from a specific table with pagination

    Args:
        schema_name: Name of the schema
        table_name: Name of the table
        limit: Maximum number of rows to return (default: 100, max: 1000)
        offset: Number of rows to skip for pagination (default: 0)

    Returns:
        Table data with column names and rows
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Verify table exists
                cur.execute(
                    """
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = %s
                """,
                    (schema_name, table_name),
                )

                if cur.fetchone()["count"] == 0:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Table '{table_name}' does not exist in schema '{schema_name}'. Please check the schema and table names and try again.",
                    )

                # Get column information
                cur.execute(
                    """
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """,
                    (schema_name, table_name),
                )

                columns = [
                    {"name": row["column_name"], "type": row["data_type"]}
                    for row in cur.fetchall()
                ]

                if not columns:
                    raise HTTPException(
                        status_code=500,
                        detail=f"No columns found for table '{table_name}'",
                    )

                # Get total row count
                cur.execute(
                    f'SELECT COUNT(*) as count FROM "{schema_name}"."{table_name}"'
                )
                total_rows = cur.fetchone()["count"]

                # Get table data with pagination
                cur.execute(
                    f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT %s OFFSET %s',
                    (limit, offset),
                )
                rows = [dict(row) for row in cur.fetchall()]

        return ShpblResponse(
            success=True,
            message=f"Retrieved {len(rows)} row(s) from '{schema_name}.{table_name}'",
            data={
                "schema_name": schema_name,
                "table_name": table_name,
                "columns": columns,
                "rows": rows,
                "total_rows": total_rows,
                "returned_rows": len(rows),
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(rows)) < total_rows,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to query table data: {str(e)}"
        )
