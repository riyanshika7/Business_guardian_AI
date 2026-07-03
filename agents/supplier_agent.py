from __future__ import annotations
"""Supplier Agent — monitors supplier dependency levels and assesses supplier relationship risk."""

import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
import logging
from datetime import datetime, timezone
from typing import Any
from google import genai
from config import GOOGLE_API_KEY, GEMINI_MODEL
from skills.forecasting_skill import compute_supplier_risk_score

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
    """Run Supplier Agent analysis.
    
    Args:
        inputs: Must contain suppliers, supplier_intelligence, supplier_news, and business_type.
    """
    agent_name = "supplier_agent"
    try:
        suppliers = inputs.get("suppliers", [])
        supplier_intel = inputs.get("supplier_intelligence")
        supplier_news = inputs.get("supplier_news", [])
        
        # 1. Validation: Suppliers list missing or empty
        if not suppliers:
            return _error_response(agent_name, "MISSING_SUPPLIER_DATA", "Suppliers dataset is missing or empty.")
            
        # 2. Validation: Supplier intelligence object missing
        if supplier_intel is None or not isinstance(supplier_intel, dict):
            return _error_response(agent_name, "MISSING_INTELLIGENCE_DATA", "Supplier intelligence dataset is missing or empty.")
            
        # Check required fields in suppliers
        for idx, sup in enumerate(suppliers):
            if "supplier_id" not in sup or "supplier_name" not in sup:
                return _error_response(agent_name, "VALIDATION_FAILED", f"Supplier record at index {idx} is missing required fields.")
                
        # 3. Cross-reference profiles, risk data, and identify high-risk suppliers
        profiles = supplier_intel.get("supplier_profiles", [])
        risk_data = supplier_intel.get("supplier_risk_data", [])
        
        intel_map = {p.get("supplier_id"): p for p in profiles if p.get("supplier_id")}
        risk_map = {r.get("supplier_id"): r for r in risk_data if r.get("supplier_id")}
        
        high_risk_suppliers = []
        for sup in suppliers:
            s_id = sup.get("supplier_id")
            s_name = sup.get("supplier_name")
            
            p_info = intel_map.get(s_id, {})
            r_info = risk_map.get(s_id, {})
            
            # Combine risk flags and checks
            risk_level = r_info.get("risk_level", "low").lower()
            risk_score = r_info.get("risk_score", 0)
            reliability = p_info.get("reliability_score", 100)
            stability = p_info.get("financial_stability_indicator", "stable").lower()
            
            reasons = []
            if risk_level == "high" or risk_score >= 70:
                reasons.append(r_info.get("primary_risk_factor", "High risk score flagged"))
            if reliability < 60:
                reasons.append(f"Low reliability score: {reliability}")
            if stability == "at_risk":
                reasons.append("Financial stability watch: at_risk")
            if p_info.get("risk_flags"):
                reasons.extend(p_info.get("risk_flags"))
                
            if reasons or risk_level in ["high", "medium"]:
                determined_level = "high" if (risk_level == "high" or reliability < 60 or stability == "at_risk") else "medium"
                high_risk_suppliers.append({
                    "supplier_id": s_id,
                    "supplier_name": s_name,
                    "risk_reason": "; ".join(reasons) if reasons else "Elevated risk flags",
                    "risk_level": determined_level
                })
                
        # 4. Dependency Score
        # Maximum dependency percentage of any active supplier, converted to integer
        dependency_percentages = []
        for s in suppliers:
            pct = s.get("dependency_percentage")
            if pct is not None:
                try:
                    dependency_percentages.append(float(pct))
                except (ValueError, TypeError):
                    pass
        max_pct = max(dependency_percentages) if dependency_percentages else 0.0
        # Dependency score 0-100
        dependency_score = int(max_pct)
        
        # 5. Compute risk score
        risk_score = compute_supplier_risk_score(high_risk_suppliers, dependency_score)
        
        # 6. Recommendation fallback
        if high_risk_suppliers:
            high_risk_names = ", ".join(s["supplier_name"] for s in high_risk_suppliers)
            fallback_rec = f"Action required on high-risk suppliers ({high_risk_names}). Initiate backup supplier agreements and monitor weekly delivery metrics."
        else:
            fallback_rec = "Supplier operational risk remains low. Review primary supplier dependency metrics quarterly and maintain contact with backup vendors."
            
        supplier_rec = fallback_rec
        
        # 7. LLM Supplier Recommendation
        if GOOGLE_API_KEY:
            try:
                client = genai.Client(api_key=GOOGLE_API_KEY)
                prompt = (
                    f"You are a Supply Chain Risk Officer. Analyze this vendor concentration and performance data:\n"
                    f"- Max Supplier Dependency: {dependency_score}%\n"
                    f"- High Risk Suppliers Count: {len(high_risk_suppliers)}\n"
                    f"- High Risk Suppliers Details: {high_risk_suppliers}\n\n"
                    f"Write a concise, actionable supplier recommendation (max 2 sentences) for the business owner. "
                    f"Do not use markdown formatting, return plain text only."
                )
                response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                if response.text:
                    supplier_rec = response.text.strip()
            except Exception as ex:
                logger.error(f"Gemini API call failed for Supplier Agent, using fallback: {ex}")
                
        result = {
            "agent": agent_name,
            "supplier_risk_score": risk_score,
            "dependency_score": dependency_score,
            "high_risk_suppliers": high_risk_suppliers,
            "supplier_recommendation": supplier_rec
        }
        return _success_response(agent_name, result)
        
    except Exception as e:
        logger.exception("Supplier Agent execution failed.")
        return _error_response(agent_name, "VALIDATION_FAILED", f"Internal validation error: {e}")
