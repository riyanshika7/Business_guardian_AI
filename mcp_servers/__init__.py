"""Local MCP modules package."""

try:
    # 1. Try absolute package import
    from mcp_servers import sheets_mcp
    from mcp_servers import calendar_mcp
    from mcp_servers import news_mcp
    from mcp_servers import supplier_intelligence_mcp
    from mcp_servers import risk_registry_mcp
except ImportError:
    try:
        # 2. Try relative package import
        from . import sheets_mcp
        from . import calendar_mcp
        from . import news_mcp
        from . import supplier_intelligence_mcp
        from . import risk_registry_mcp
    except ImportError:
        # 3. Fallback for direct script execution
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import sheets_mcp
        import calendar_mcp
        import news_mcp
        import supplier_intelligence_mcp
        import risk_registry_mcp


