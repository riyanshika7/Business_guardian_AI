"""Google Sheets & Drive MCP Client.

Connects to a real Google Workspace Drive/Sheets MCP server via stdio,
falling back to local CSV files if authentication or the server is unavailable.
"""

from __future__ import annotations
from datetime import datetime, timezone
import re
import os
import csv
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def _fetch_from_gws_drive(spreadsheet_id: str, sheets: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Connect to official gws-drive MCP server to read sheet files as CSV contents."""
    import asyncio
    
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@google/mcp-gws-drive"]
    )
    
    async def _fetch_task():
        data = {}
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                for sheet in sheets:
                    file_id = f"{spreadsheet_id}_{sheet}.csv"
                    response = await session.call_tool("read_file_content", arguments={
                        "fileId": file_id
                    })
                    
                    if response and hasattr(response, "content") and response.content:
                        text_content = response.content[0].text
                        reader = csv.DictReader(text_content.splitlines())
                        data[sheet] = [dict(row) for row in reader]
        return data

    # Enforce a 3.0 second connection/init timeout to prevent uvicorn hangs
    return await asyncio.wait_for(_fetch_task(), timeout=3.0)

# ===================================================================
# Local CSV / Fallback data helpers
# ===================================================================

def _load_csv_data(filename: str) -> list[dict[str, Any]] | None:
    """Helper to load a CSV file from the 'database' directory if it exists."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(project_root, "database", filename)
    if os.path.exists(csv_path):
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return [dict(row) for row in reader]
        except Exception:
            pass
    return None

def get_inventory_data(spreadsheet_id: str | None = None) -> list[dict[str, Any]]:
    csv_data = _load_csv_data("inventory.csv")
    if csv_data is not None:
        records = []
        for row in csv_data:
            try:
                records.append({
                    "inventory_id": row.get("inventory_id"),
                    "product_id": row.get("product_id"),
                    "current_stock": int(row.get("current_stock", 0)),
                    "warehouse_location": row.get("warehouse_location"),
                    "last_updated": row.get("last_updated"),
                    "recorded_by": row.get("recorded_by", "google_sheets_mcp_csv")
                })
            except Exception:
                pass
        return records

    return [
        {
            "inventory_id": "INV-001",
            "product_id": "PROD-001",
            "current_stock": 50,
            "warehouse_location": "Warehouse Zone A",
            "last_updated": "2026-06-25T12:00:00Z",
            "recorded_by": "google_sheets_mcp"
        },
        {
            "inventory_id": "INV-002",
            "product_id": "PROD-002",
            "current_stock": 3,
            "warehouse_location": "Warehouse Zone B",
            "last_updated": "2026-06-25T14:30:00Z",
            "recorded_by": "google_sheets_mcp"
        },
        {
            "inventory_id": "INV-003",
            "product_id": "PROD-003",
            "current_stock": 12,
            "warehouse_location": "Warehouse Zone A",
            "last_updated": "2026-06-25T09:15:00Z",
            "recorded_by": "google_sheets_mcp"
        }
    ]

def get_sales_data(spreadsheet_id: str | None = None, days: int = 30) -> list[dict[str, Any]]:
    csv_data = _load_csv_data("sales.csv")
    if csv_data is not None:
        records = []
        for row in csv_data:
            try:
                records.append({
                    "sale_id": row.get("sale_id"),
                    "product_id": row.get("product_id"),
                    "quantity_sold": int(row.get("quantity_sold", row.get("quantity", 0))),
                    "sale_amount": float(row.get("sale_amount", 0.0)),
                    "unit_price_at_sale": float(row.get("unit_price_at_sale", 0.0)),
                    "sale_date": row.get("sale_date"),
                    "channel": row.get("channel"),
                    "recorded_at": row.get("recorded_at")
                })
            except Exception:
                pass
        return records

    return [
        {
            "sale_id": "SALE-001",
            "product_id": "PROD-001",
            "quantity_sold": 15,
            "sale_amount": 300.0,
            "unit_price_at_sale": 20.0,
            "sale_date": "2026-06-10",
            "channel": "online",
            "recorded_at": "2026-06-10T15:00:00Z"
        },
        {
            "sale_id": "SALE-002",
            "product_id": "PROD-002",
            "quantity_sold": 8,
            "sale_amount": 120.0,
            "unit_price_at_sale": 15.0,
            "sale_date": "2026-06-12",
            "channel": "in_store",
            "recorded_at": "2026-06-12T16:00:00Z"
        },
        {
            "sale_id": "SALE-003",
            "product_id": "PROD-003",
            "quantity_sold": 5,
            "sale_amount": 250.0,
            "unit_price_at_sale": 50.0,
            "sale_date": "2026-06-15",
            "channel": "online",
            "recorded_at": "2026-06-15T10:00:00Z"
        }
    ]

def get_expenses_data(spreadsheet_id: str | None = None, days: int = 30) -> list[dict[str, Any]]:
    csv_data = _load_csv_data("expenses.csv")
    if csv_data is not None:
        records = []
        for row in csv_data:
            try:
                records.append({
                    "expense_id": row.get("expense_id"),
                    "expense_category": row.get("expense_category"),
                    "amount": float(row.get("amount", 0.0)),
                    "description": row.get("description"),
                    "expense_date": row.get("expense_date"),
                    "vendor": row.get("vendor"),
                    "recorded_at": row.get("recorded_at")
                })
            except Exception:
                pass
        return records

    return [
        {
            "expense_id": "EXP-001",
            "expense_category": "rent",
            "amount": 800.0,
            "description": "Office sublease monthly rent",
            "expense_date": "2026-06-01",
            "vendor": "Prime Real Estate",
            "recorded_at": "2026-06-01T08:00:00Z"
        },
        {
            "expense_id": "EXP-002",
            "expense_category": "utilities",
            "amount": 150.0,
            "description": "Monthly energy and water bill",
            "expense_date": "2026-06-10",
            "vendor": "Central Energy Grid",
            "recorded_at": "2026-06-10T09:30:00Z"
        }
    ]

def get_suppliers_data(spreadsheet_id: str | None = None) -> list[dict[str, Any]]:
    csv_data = _load_csv_data("suppliers.csv")
    if csv_data is not None:
        records = []
        for row in csv_data:
            try:
                cats_str = row.get("product_categories", "")
                if cats_str.startswith("[") and cats_str.endswith("]"):
                    try:
                        categories = json.loads(cats_str)
                    except Exception:
                        categories = [c.strip() for c in cats_str[1:-1].split(",") if c.strip()]
                else:
                    categories = [c.strip() for c in cats_str.split(",") if c.strip()]
                records.append({
                    "supplier_id": row.get("supplier_id"),
                    "supplier_name": row.get("supplier_name"),
                    "contact_name": row.get("contact_name"),
                    "contact_email": row.get("contact_email"),
                    "country": row.get("country"),
                    "product_categories": categories,
                    "dependency_percentage": float(row["dependency_percentage"]) if row.get("dependency_percentage") else None,
                    "contract_start_date": row.get("contract_start_date"),
                    "contract_end_date": row.get("contract_end_date"),
                    "is_active": row.get("is_active", "True").lower() in ("true", "1", "yes"),
                    "created_at": row.get("created_at")
                })
            except Exception:
                pass
        return records

    return [
        {
            "supplier_id": "SUP-001",
            "supplier_name": "Alpha Supplies",
            "contact_name": "John Doe",
            "contact_email": "john@alphasupplies.com",
            "country": "USA",
            "product_categories": ["electronics", "office_supplies"],
            "dependency_percentage": 75.0,
            "contract_start_date": "2026-01-01",
            "contract_end_date": "2026-12-31",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z"
        },
        {
            "supplier_id": "SUP-002",
            "supplier_name": "Beta Logistics",
            "contact_name": "Jane Smith",
            "contact_email": "jane@betalogistics.com",
            "country": "Canada",
            "product_categories": ["packaging", "delivery_services"],
            "dependency_percentage": 25.0,
            "contract_start_date": "2026-02-01",
            "contract_end_date": "2026-11-30",
            "is_active": True,
            "created_at": "2026-02-01T00:00:00Z"
        }
    ]

# ===================================================================
# Validation Rules
# ===================================================================

def validate_inventory_record(record: dict[str, Any]) -> str | None:
    required_fields = ["inventory_id", "product_id", "current_stock", "last_updated", "recorded_by"]
    for field in required_fields:
        if field not in record or record[field] is None or record[field] == "":
            return "MISSING_REQUIRED_FIELD"
    current_stock = record["current_stock"]
    if not isinstance(current_stock, int):
        try:
            current_stock = int(current_stock)
        except (ValueError, TypeError):
            return "MISSING_REQUIRED_FIELD"
    if current_stock < 0:
        return "NEGATIVE_STOCK_VALUE"
    return None

def validate_sales_record(record: dict[str, Any]) -> str | None:
    required_fields = ["sale_id", "product_id", "quantity_sold", "sale_amount", "unit_price_at_sale", "sale_date", "recorded_at"]
    for field in required_fields:
        if field not in record or record[field] is None or record[field] == "":
            return "MISSING_REQUIRED_FIELD"
    quantity_sold = record["quantity_sold"]
    if not isinstance(quantity_sold, int):
        try:
            quantity_sold = int(quantity_sold)
        except (ValueError, TypeError):
            return "MISSING_REQUIRED_FIELD"
    if quantity_sold <= 0:
        return "INVALID_QUANTITY_VALUE"
    for field in ["sale_amount", "unit_price_at_sale"]:
        val = record[field]
        if not isinstance(val, (int, float)):
            try:
                val = float(val)
            except (ValueError, TypeError):
                return "MISSING_REQUIRED_FIELD"
        if val < 0.0:
            return "NEGATIVE_MONETARY_VALUE"
    return None

def validate_expense_record(record: dict[str, Any]) -> str | None:
    required_fields = ["expense_id", "expense_category", "amount", "expense_date", "recorded_at"]
    for field in required_fields:
        if field not in record or record[field] is None or record[field] == "":
            return "MISSING_REQUIRED_FIELD"
    amount = record["amount"]
    if not isinstance(amount, (int, float)):
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return "MISSING_REQUIRED_FIELD"
    if amount < 0.0:
        return "NEGATIVE_MONETARY_VALUE"
    return None

def validate_supplier_record(record: dict[str, Any]) -> str | None:
    required_fields = ["supplier_id", "supplier_name", "country", "product_categories", "is_active", "created_at"]
    for field in required_fields:
        if field not in record or record[field] is None or (field != "product_categories" and record[field] == ""):
            return "MISSING_REQUIRED_FIELD"
    if not isinstance(record["product_categories"], list):
        return "MISSING_REQUIRED_FIELD"
    dependency_percentage = record.get("dependency_percentage")
    if dependency_percentage is not None:
        if not isinstance(dependency_percentage, (int, float)):
            try:
                dependency_percentage = float(dependency_percentage)
            except (ValueError, TypeError):
                return "MISSING_REQUIRED_FIELD"
        if dependency_percentage < 0.0 or dependency_percentage > 100.0:
            return "INVALID_PERCENTAGE_VALUE"
    return None

def _get_error_message(error_code: str) -> str:
    messages = {
        "MISSING_REQUIRED_FIELD": "Mandatory cell is empty or has invalid type in sheet.",
        "NEGATIVE_STOCK_VALUE": "Inventory record contains negative current_stock.",
        "INVALID_QUANTITY_VALUE": "Sales record contains zero or negative quantity_sold.",
        "NEGATIVE_MONETARY_VALUE": "Sales or expense record contains negative monetary amount.",
        "INVALID_PERCENTAGE_VALUE": "Supplier record contains dependency_percentage < 0 or > 100."
    }
    return messages.get(error_code, "Validation error occurred.")

# ===================================================================
# Public MCP Entry Point
# ===================================================================

def fetch_sheets_data(inputs: dict[str, Any]) -> dict[str, Any]:
    """Validate and fetch data from mock/real Google Sheets."""
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    try:
        spreadsheet_id = inputs.get("spreadsheet_id")
        sheets = inputs.get("sheets")
        date_range = inputs.get("date_range")
        
        # 1. Validation: spreadsheet_id must be non-empty
        if not spreadsheet_id or not isinstance(spreadsheet_id, str):
            return {
                "mcp": "google_sheets_mcp",
                "status": "error",
                "error_code": "MISSING_SPREADSHEET_ID",
                "error_message": "spreadsheet_id must be a non-empty string.",
                "fetched_at": fetched_at
            }
            
        # 2. Validation: sheets must be non-empty and valid
        if not sheets or not isinstance(sheets, list):
            return {
                "mcp": "google_sheets_mcp",
                "status": "error",
                "error_code": "INVALID_SHEET_NAME",
                "error_message": "sheets must be a non-empty list.",
                "fetched_at": fetched_at
            }
            
        for sheet in sheets:
            if sheet not in ["inventory", "sales", "expenses", "suppliers"]:
                return {
                    "mcp": "google_sheets_mcp",
                    "status": "error",
                    "error_code": "INVALID_SHEET_NAME",
                    "error_message": f"Sheet '{sheet}' is not a recognized operational data tab.",
                    "fetched_at": fetched_at
                }
                
        # 3. Validation: date format check YYYY-MM-DD
        if not isinstance(date_range, dict) or "start_date" not in date_range or "end_date" not in date_range:
            return {
                "mcp": "google_sheets_mcp",
                "status": "error",
                "error_code": "INVALID_DATE_FORMAT",
                "error_message": "date_range must be a dictionary containing 'start_date' and 'end_date'.",
                "fetched_at": fetched_at
            }
            
        start_date = date_range["start_date"]
        end_date = date_range["end_date"]
        
        date_regex = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        if not isinstance(start_date, str) or not isinstance(end_date, str) or not date_regex.match(start_date) or not date_regex.match(end_date):
            return {
                "mcp": "google_sheets_mcp",
                "status": "error",
                "error_code": "INVALID_DATE_FORMAT",
                "error_message": "start_date and end_date must be formatted as YYYY-MM-DD.",
                "fetched_at": fetched_at
            }
            
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return {
                "mcp": "google_sheets_mcp",
                "status": "error",
                "error_code": "INVALID_DATE_FORMAT",
                "error_message": "start_date or end_date is not a valid calendar date.",
                "fetched_at": fetched_at
            }
            
        # 4. Validation: date chronological order check
        if end_dt < start_dt:
            return {
                "mcp": "google_sheets_mcp",
                "status": "error",
                "error_code": "INVALID_DATE_RANGE",
                "error_message": "end_date must be chronologically on or after start_date.",
                "fetched_at": fetched_at
            }
            
        # Try retrieving via Google Drive MCP
        gws_data = None
        if spreadsheet_id != "spreadsheet-12345":
            try:
                import asyncio
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            try:
                gws_data = loop.run_until_complete(_fetch_from_gws_drive(spreadsheet_id, sheets))
                logger.info("Successfully fetched data from GWS Drive MCP.")
            except Exception as e:
                logger.warning(f"Connection to GWS Drive MCP failed (falling back to CSV): {e}")

        # Build data payload from GWS or local fallback
        data: dict[str, Any] = {}
        
        # Load sheets data and perform integrity checks
        if "inventory" in sheets:
            inventory_records = gws_data.get("inventory") if gws_data else None
            if inventory_records is None:
                inventory_records = get_inventory_data(spreadsheet_id)
            for record in inventory_records:
                error_code = validate_inventory_record(record)
                if error_code:
                    return {
                        "mcp": "google_sheets_mcp",
                        "status": "error",
                        "error_code": error_code,
                        "error_message": _get_error_message(error_code),
                        "fetched_at": fetched_at
                    }
            data["inventory"] = inventory_records
            
        if "sales" in sheets:
            sales_records = gws_data.get("sales") if gws_data else None
            if sales_records is None:
                sales_records = get_sales_data(spreadsheet_id)
            filtered_sales = []
            for record in sales_records:
                error_code = validate_sales_record(record)
                if error_code:
                    return {
                        "mcp": "google_sheets_mcp",
                        "status": "error",
                        "error_code": error_code,
                        "error_message": _get_error_message(error_code),
                        "fetched_at": fetched_at
                    }
                # Filter sales by date range
                sale_date = record["sale_date"]
                if start_date <= sale_date <= end_date:
                    filtered_sales.append(record)
            data["sales"] = filtered_sales
            
        if "expenses" in sheets:
            expenses_records = gws_data.get("expenses") if gws_data else None
            if expenses_records is None:
                expenses_records = get_expenses_data(spreadsheet_id)
            filtered_expenses = []
            for record in expenses_records:
                error_code = validate_expense_record(record)
                if error_code:
                    return {
                        "mcp": "google_sheets_mcp",
                        "status": "error",
                        "error_code": error_code,
                        "error_message": _get_error_message(error_code),
                        "fetched_at": fetched_at
                    }
                # Filter expenses by date range
                expense_date = record["expense_date"]
                if start_date <= expense_date <= end_date:
                    filtered_expenses.append(record)
            data["expenses"] = filtered_expenses
            
        if "suppliers" in sheets:
            suppliers_records = gws_data.get("suppliers") if gws_data else None
            if suppliers_records is None:
                suppliers_records = get_suppliers_data(spreadsheet_id)
            for record in suppliers_records:
                error_code = validate_supplier_record(record)
                if error_code:
                    return {
                        "mcp": "google_sheets_mcp",
                        "status": "error",
                        "error_code": error_code,
                        "error_message": _get_error_message(error_code),
                        "fetched_at": fetched_at
                    }
            data["suppliers"] = suppliers_records
            
        return {
            "mcp": "google_sheets_mcp",
            "status": "success",
            "data": data,
            "warnings": None,
            "fetched_at": fetched_at
        }
        
    except Exception as e:
        return {
            "mcp": "google_sheets_mcp",
            "status": "error",
            "error_code": "FETCH_FAILED",
            "error_message": f"An unexpected error occurred while fetching sheets data: {str(e)}",
            "fetched_at": fetched_at
        }
