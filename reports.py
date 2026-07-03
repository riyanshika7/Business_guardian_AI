"""Streamlit reports viewer for Business Guardian AI."""

from __future__ import annotations
import json
from database import db

try:
    import streamlit as st
    _STREAMLIT_AVAILABLE = True
except ImportError:
    st = None  # type: ignore[assignment]
    _STREAMLIT_AVAILABLE = False

if not _STREAMLIT_AVAILABLE:
    raise SystemExit(
        "Streamlit is required to run the reports dashboard.\n"
        "Install it with:  pip install streamlit\n"
        "Then run:         streamlit run reports.py"
    )

st.set_page_config(
    page_title="Guardian Reports Archive",
    page_icon="📁",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0f121d;
        color: #e2e8f0;
    }
    .report-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("📁 Operational Reports Archive")
st.markdown("Browse and inspect previously approved and finalized multi-agent audits.")

# Search bar
search_id = st.text_input("Filter by Business ID", "BIZ-101")

if st.button("Search Archive"):
    reports = db.fetch_all(
        "SELECT * FROM reports WHERE business_id = ? ORDER BY generated_at DESC", 
        (search_id,)
    )
    
    if not reports:
        st.info(f"No reports found for Business ID '{search_id}' in the database.")
    else:
        st.success(f"Discovered {len(reports)} archived reports.")
        for r in reports:
            rep_id = r.get("report_id")
            run_id = r.get("run_id")
            generated_at = r.get("generated_at")
            sys_status = r.get("system_status")
            
            # Try to deserialize content
            content_str = r.get("content")
            content = None
            if content_str:
                if isinstance(content_str, dict):
                    content = content_str
                else:
                    try:
                        content = json.loads(content_str)
                    except ValueError:
                        pass
            
            v_status = "N/A"
            conf_score = "N/A"
            if content:
                eval_report = content.get("agent_reports", {}).get("evaluation_report") or {}
                v_status = eval_report.get("validation_status", "N/A")
                conf_score = eval_report.get("confidence_score", "N/A")
            
            with st.expander(f"Report Run: {run_id[:8]}... | Finalized: {generated_at} | Status: {sys_status.upper()}"):
                st.markdown(f"**Full Run ID:** `{run_id}`")
                st.markdown(f"**Confidence Score:** `{conf_score}/100` | **Validation Status:** `{v_status}`")
                
                if content:
                    try:
                        st.markdown("---")
                        
                        # Display Scores
                        scores = content.get("scores", {})
                        st.subheader("Operational Scores")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Business Health", scores.get("business_health_score"))
                        c2.metric("Inventory Risk", scores.get("inventory_risk"))
                        c3.metric("Finance Risk", scores.get("finance_risk"))
                        c4.metric("Supplier Risk", scores.get("supplier_risk"))
                        
                        # Display Actions
                        st.subheader("Recommended Priorities")
                        recs = content.get("top_recommendations", [])
                        for rec in recs:
                            st.markdown(f"**Rank {rec.get('rank')} - {rec.get('action_title')}**")
                            st.markdown(f"*Domain: {rec.get('target_domain')} | Urgency: {rec.get('urgency')}*")
                            st.markdown(rec.get("action_description"))
                            st.markdown("---")
                            
                        # Display Report Draft
                        comm = content.get("communication_draft", {})
                        rep_draft = comm.get("report_draft") or {}
                        st.subheader("Report Summary Draft")
                        st.info(rep_draft.get("executive_summary", "No summary generated."))
                        st.warning(rep_draft.get("risk_summary", "No risk summary generated."))
                        
                    except Exception as e:
                        st.error(f"Failed to parse report content: {e}")
                        st.text(content_str)
else:
    st.info("Enter a Business ID above and click Search Archive to retrieve operational records.")
