from __future__ import annotations
"""Finance Agent — analyzes revenue, expenses, and profitability to assess financial health."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import logging
from datetime import datetime, timezone
from typing import Any
from google import genai
from config import GOOGLE_API_KEY, GEMINI_MODEL
from skills.forecasting_skill import compute_finance_risk_score

logger = logging.getLogger(__name__)

def _success_response(agent_name: str, data: dict) -> dict:
    data["status"] = "success"
    data["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return data

def _error_response(agent_name: str, error_code: str, message: str) -> dict:
    return {
        "agent": agent_name,
        "status": "error",
        "error_code": error_code,
        "error_message": message,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }

def run(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run Finance Agent analysis.
    
    Args:
        inputs: Must contain sales, expenses, period_days, and business_type.
    """
    agent_name = "finance_agent"
    try:
        sales = inputs.get("sales")
        expenses = inputs.get("expenses")
        period_days = inputs.get("period_days", 30)
        
        # 1. Validation: sales or expenses are missing
        if sales is None or expenses is None:
            return _error_response(agent_name, "MISSING_FINANCIAL_DATA", "Sales or expenses data is missing.")
            
        # 2. Validation: period_days range check
        try:
            period_days = int(period_days)
            if period_days <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return _error_response(agent_name, "INVALID_PERIOD", "Analysis period must be a positive integer.")
            
        # 3. Validation: sales & expenses records integrity
        for idx, sale in enumerate(sales):
            if "sale_id" not in sale or "sale_amount" not in sale:
                return _error_response(agent_name, "VALIDATION_FAILED", f"Sales record at index {idx} is missing required fields.")
            if float(sale.get("sale_amount", 0)) < 0:
                return _error_response(agent_name, "VALIDATION_FAILED", "Negative sale amount detected.")
                
        for idx, exp in enumerate(expenses):
            if "expense_id" not in exp or "amount" not in exp:
                return _error_response(agent_name, "VALIDATION_FAILED", f"Expense record at index {idx} is missing required fields.")
            if float(exp.get("amount", 0)) < 0:
                return _error_response(agent_name, "VALIDATION_FAILED", "Negative expense amount detected.")
                
        # 4. Calculation
        total_revenue = sum(float(s.get("sale_amount", 0.0)) for s in sales)
        total_expenses = sum(float(e.get("amount", 0.0)) for e in expenses)
        net_profit = total_revenue - total_expenses
        
        if total_revenue > 0:
            profit_margin = (net_profit / total_revenue) * 100.0
        else:
            profit_margin = 0.0
            
        # Round to 2 decimal places
        total_revenue = round(total_revenue, 2)
        total_expenses = round(total_expenses, 2)
        net_profit = round(net_profit, 2)
        profit_margin = round(profit_margin, 2)
        
        # 5. Compute risk score
        risk_score = compute_finance_risk_score(profit_margin, net_profit, total_revenue)
        
        # 6. Rule-based fallback recommendation
        if profit_margin < 0.0:
            fallback_rec = "The business is currently operating at a net loss. Focus immediately on cutting utility and overhead expenses, and review pricing structures to recover margins."
        elif profit_margin < 10.0:
            fallback_rec = "Profit margins are thin. Monitor operational costs closely and explore new channels or sales volume drivers to boost revenue."
        else:
            fallback_rec = "Financial health is currently stable with healthy profit margins. Continue maintaining expense controls and consider investing surplus cash into growth."
            
        financial_rec = fallback_rec
        
        # 7. LLM Financial Recommendation Generation
        if GOOGLE_API_KEY:
            try:
                client = genai.Client(api_key=GOOGLE_API_KEY)
                prompt = (
                    f"You are a Senior Financial Advisor. Analyze this small business's performance over {period_days} days:\n"
                    f"- Total Revenue: ${total_revenue:.2f}\n"
                    f"- Total Expenses: ${total_expenses:.2f}\n"
                    f"- Net Profit: ${net_profit:.2f}\n"
                    f"- Profit Margin: {profit_margin:.2f}%\n\n"
                    f"Write a concise, actionable financial recommendation (max 2 sentences) for the business owner. "
                    f"Do not use markdown styling or list formatting, return plain text only."
                )
                response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                if response.text:
                    financial_rec = response.text.strip()
            except Exception as ex:
                logger.error(f"Gemini API call failed for Finance Agent, using rule-based fallback: {ex}")
                
        result = {
            "agent": agent_name,
            "finance_risk_score": risk_score,
            "profit_margin": profit_margin,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "financial_recommendation": financial_rec
        }
        return _success_response(agent_name, result)
        
    except Exception as e:
        logger.exception("Finance Agent execution failed.")
        return _error_response(agent_name, "VALIDATION_FAILED", f"Internal validation error: {e}")
