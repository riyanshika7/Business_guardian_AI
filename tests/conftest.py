"""Global pytest fixtures and mocks configuration."""

import pytest
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is on PYTHONPATH
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config to trigger ADK compatibility runtime patches
import config  # noqa: F401


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_adk_session_service():
    """Ensure InMemorySessionService.create_session and append_event are awaitable.

    In google-adk < 1.x these methods are synchronous; workflow.py awaits them.
    This fixture is a no-op on ADK 1.x+ where they are already async coroutines.
    """
    from google.adk.sessions import InMemorySessionService
    import inspect

    original_create = InMemorySessionService.create_session
    original_append = InMemorySessionService.append_event

    if not inspect.iscoroutinefunction(original_create):
        async def async_create_session(self, *, app_name, user_id, state=None, session_id=None):
            return original_create(self, app_name=app_name, user_id=user_id,
                                   state=state, session_id=session_id)
        InMemorySessionService.create_session = async_create_session

    if not inspect.iscoroutinefunction(original_append):
        async def async_append_event(self, session, event):
            return original_append(self, session, event)
        InMemorySessionService.append_event = async_append_event

    yield

    # Restore originals after each test
    InMemorySessionService.create_session = original_create
    InMemorySessionService.append_event = original_append


@pytest.fixture
def mock_db(monkeypatch):
    """Fixture to mock sqlite database operations."""
    db_records = {}

    def mock_fetch_all(query, params=()):
        if "compliance_events" in query.lower():
            return [
                {
                    "event_id": "EVT-001",
                    "event_name": "Health Audit",
                    "event_type": "regulatory",
                    "due_date": "2026-07-10",
                    "description": "Annual regulatory inspection",
                    "responsible_party": "ops_manager",
                    "status": "pending",
                    "recurrence": "annual",
                    "created_at": "2026-06-01T00:00:00Z"
                }
            ]
        elif "products" in query.lower():
            return [
                {
                    "product_id": "PROD-001",
                    "product_name": "Premium Beans",
                    "category": "Beverages",
                    "sku": "PB-01",
                    "unit_cost": 5.50,
                    "unit_price": 12.00,
                    "reorder_point": 20,
                    "reorder_quantity": 50,
                    "supplier_id": "SUP-001",
                    "is_active": 1,
                    "created_at": "2026-06-26T12:00:00Z"
                }
            ]
        return []

    def mock_insert_row(table, data):
        db_records[table] = data
        return "mocked-uuid-123"

    def mock_execute_query(query, params=()):
        pass

    from database import db
    monkeypatch.setattr(db, "fetch_all", mock_fetch_all)
    monkeypatch.setattr(db, "insert_row", mock_insert_row)
    monkeypatch.setattr(db, "execute_query", mock_execute_query)
    return db_records


@pytest.fixture
def baseline_inputs():
    """Valid payloads matching agent operational structures."""
    return {
        "products": [
            {
                "product_id": "PROD-001",
                "product_name": "Premium Beans",
                "category": "Beverages",
                "sku": "PB-01",
                "unit_cost": 5.50,
                "unit_price": 12.00,
                "reorder_point": 20,
                "reorder_quantity": 50,
                "supplier_id": "SUP-001",
                "is_active": 1,
                "created_at": "2026-06-26T12:00:00Z"
            }
        ],
        "inventory": [
            {
                "inventory_id": "INV-001",
                "product_id": "PROD-001",
                "current_stock": 15,
                "warehouse_location": "Aisle 3",
                "last_updated": "2026-06-26T10:00:00Z",
                "recorded_by": "worker"
            }
        ],
        "sales": [
            {
                "sale_id": "SALE-001",
                "product_id": "PROD-001",
                "quantity_sold": 5,
                "sale_amount": 60.00,
                "unit_price_at_sale": 12.00,
                "sale_date": "2026-06-26",
                "channel": "retail",
                "recorded_at": "2026-06-26T12:00:00Z"
            }
        ],
        "expenses": [
            {
                "expense_id": "EXP-001",
                "expense_category": "utilities",
                "amount": 120.00,
                "description": "Electricity bill",
                "expense_date": "2026-06-26",
                "vendor": "Power Co",
                "recorded_at": "2026-06-26T10:00:00Z"
            }
        ],
        "suppliers": [
            {
                "supplier_id": "SUP-001",
                "supplier_name": "Global Supplier",
                "contact_name": "Alice",
                "contact_email": "alice@global.com",
                "country": "UK",
                "product_categories": "Beverages",
                "dependency_percentage": 40.0,
                "contract_start_date": "2026-01-01",
                "contract_end_date": "2026-12-31",
                "is_active": 1,
                "created_at": "2026-01-01T00:00:00Z"
            }
        ],
        "compliance_events": [
            {
                "event_id": "EVT-001",
                "event_name": "Health Audit",
                "event_type": "regulatory",
                "due_date": "2026-07-10",
                "description": "Annual regulatory inspection",
                "responsible_party": "ops_manager",
                "status": "pending",
                "recurrence": "annual",
                "created_at": "2026-06-01T00:00:00Z"
            }
        ]
    }
