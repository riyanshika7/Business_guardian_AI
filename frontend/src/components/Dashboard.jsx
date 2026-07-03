import React, { useState } from 'react';
import { ShieldAlert, Zap, Box, TrendingUp, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

export default function Dashboard({ history, reports }) {
  const [expandedReport, setExpandedReport] = useState(null);

  if (!history || history.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', marginTop: '2rem' }}>
        <Zap size={48} className="text-muted" style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
        <h3 className="text-secondary" style={{ fontSize: '1.25rem' }}>No Historical Data</h3>
        <p className="text-muted mt-2">Run an analysis to generate operational risk insights.</p>
      </div>
    );
  }

  const latestScore = history[0];
  const previousScore = history.length > 1 ? history[1] : null;

  const getTrend = (current, previous) => {
    if (!previous) return null;
    const diff = current - previous;
    if (diff > 0) return <span className="text-error" style={{ fontSize: '0.85rem' }}>+{diff.toFixed(1)} (Worse)</span>;
    if (diff < 0) return <span className="text-success" style={{ fontSize: '0.85rem' }}>{diff.toFixed(1)} (Better)</span>;
    return <span className="text-secondary" style={{ fontSize: '0.85rem' }}>Stable</span>;
  };

  const getScoreColor = (score) => {
    if (score >= 70) return 'var(--status-error)';
    if (score >= 40) return 'var(--status-warning)';
    return 'var(--status-success)';
  };

  const renderMetric = (label, key, icon, reverseColor = false) => {
    const val = latestScore[key];
    if (val === undefined || val === null) return null;
    
    let color = getScoreColor(val);
    if (reverseColor) {
      if (val >= 70) color = 'var(--status-success)';
      else if (val >= 40) color = 'var(--status-warning)';
      else color = 'var(--status-error)';
    }

    return (
      <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div className="flex items-center justify-between text-muted">
          <span style={{ fontSize: '0.9rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
          {icon}
        </div>
        <div className="flex items-center justify-between">
          <span style={{ fontSize: '2.5rem', fontWeight: 700, color }}>{val}</span>
          {previousScore && getTrend(val, previousScore[key])}
        </div>
      </div>
    );
  };

  const renderReportContent = (report) => {
    let content = report.content;
    if (!content) return <p className="text-muted">No content available.</p>;

    if (typeof content === 'string') {
      try { content = JSON.parse(content); } catch { return <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}>{content}</div>; }
    }

    // Extract meaningful sections from the full pipeline state
    const agentReports = content.agent_reports || {};
    const mcpData = content.mcp_data || {};
    const auditTrail = content.audit_trail || [];
    const scores = {};

    // Extract scores from business_risk_report
    const bizRisk = agentReports.business_risk_report || {};
    const breakdown = bizRisk.risk_breakdown || {};
    scores.businessRisk = bizRisk.business_risk_score;
    scores.inventory = breakdown.inventory_risk_score;
    scores.finance = breakdown.finance_risk_score;
    scores.supplier = breakdown.supplier_risk_score;
    scores.compliance = breakdown.compliance_risk_score;

    const strategyReport = agentReports.strategy_report || {};
    scores.healthScore = strategyReport.business_health_score;

    const commDraft = agentReports.communication_draft || {};
    const criticalRisks = bizRisk.critical_risks || [];

    const sectionStyle = { marginBottom: '1.5rem' };
    const headingStyle = { fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-blue)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.75rem', paddingBottom: '0.35rem', borderBottom: '1px solid var(--border-light)' };
    const cardBg = { background: 'rgba(0,0,0,0.15)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-sm)', fontSize: '0.9rem' };

    const getScoreColor = (val, reverse) => {
      if (val == null) return 'var(--text-muted)';
      if (reverse) return val >= 70 ? 'var(--status-success)' : val >= 40 ? 'var(--status-warning)' : 'var(--status-error)';
      return val >= 70 ? 'var(--status-error)' : val >= 40 ? 'var(--status-warning)' : 'var(--status-success)';
    };

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>

        {/* Business Overview */}
        <div style={sectionStyle}>
          <div style={headingStyle}>Business Overview</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div style={cardBg}><span className="text-muted">Business: </span><strong>{content.business_name || '—'}</strong></div>
            <div style={cardBg}><span className="text-muted">Type: </span><strong style={{ textTransform: 'capitalize' }}>{content.business_type || '—'}</strong></div>
            <div style={cardBg}><span className="text-muted">Analysis Period: </span><strong>{content.period_days || '—'} days</strong></div>
            <div style={cardBg}><span className="text-muted">Status: </span><strong style={{ textTransform: 'capitalize', color: content.system_status === 'success' ? 'var(--status-success)' : 'var(--status-warning)' }}>{content.system_status || '—'}</strong></div>
          </div>
        </div>

        {/* Risk Scores */}
        {scores.businessRisk != null && (
          <div style={sectionStyle}>
            <div style={headingStyle}>Risk Scores</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
              {[
                { label: 'Health Score', val: scores.healthScore, reverse: true },
                { label: 'Overall Risk', val: scores.businessRisk },
                { label: 'Inventory', val: scores.inventory },
                { label: 'Finance', val: scores.finance },
                { label: 'Supplier', val: scores.supplier },
                { label: 'Compliance', val: scores.compliance },
              ].map(({ label, val, reverse }) => (
                <div key={label} style={{ ...cardBg, textAlign: 'center' }}>
                  <div className="text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.25rem' }}>{label}</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: getScoreColor(val, reverse) }}>
                    {val != null ? `${val}/100` : '—'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Critical Risks */}
        {criticalRisks.length > 0 && (
          <div style={sectionStyle}>
            <div style={headingStyle}>Critical Risks</div>
            {criticalRisks.map((risk, idx) => (
              <div key={idx} style={{ ...cardBg, marginBottom: '0.5rem', borderLeft: '3px solid var(--status-error)', display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{risk.domain}</span>
                <span style={{ fontWeight: 700, color: getScoreColor(risk.score) }}>{risk.score}/100 <span className="text-muted" style={{ fontWeight: 400, fontSize: '0.8rem' }}>({risk.severity})</span></span>
              </div>
            ))}
          </div>
        )}

        {/* Top Recommendations */}
        {strategyReport.priority_1_action && (
          <div style={sectionStyle}>
            <div style={headingStyle}>Top Recommendations</div>
            {[strategyReport.priority_1_action, strategyReport.priority_2_action, strategyReport.priority_3_action]
              .filter(Boolean)
              .map((action, idx) => (
                <div key={idx} style={{ ...cardBg, marginBottom: '0.5rem', borderLeft: `3px solid ${action.urgency === 'immediate' ? 'var(--status-error)' : action.urgency === 'this_week' ? 'var(--status-warning)' : 'var(--accent-blue)'}` }}>
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{idx + 1}. {action.action_title}</div>
                  <div className="text-secondary" style={{ fontSize: '0.85rem' }}>{action.action_description}</div>
                  <div style={{ marginTop: '0.35rem', fontSize: '0.8rem' }}>
                    <span className="text-muted">Urgency: </span>
                    <span style={{ textTransform: 'uppercase', fontWeight: 600, color: action.urgency === 'immediate' ? 'var(--status-error)' : 'var(--status-warning)' }}>{action.urgency}</span>
                    <span className="text-muted" style={{ marginLeft: '1rem' }}>Impact: </span>
                    <span>{action.expected_impact}</span>
                  </div>
                </div>
              ))}
          </div>
        )}

        {/* CEO Briefing */}
        {commDraft.ceo_briefing && (
          <div style={sectionStyle}>
            <div style={headingStyle}>CEO Briefing</div>
            <div style={{ ...cardBg, whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{commDraft.ceo_briefing}</div>
          </div>
        )}

        {/* Email Draft */}
        {commDraft.email_draft && (
          <div style={sectionStyle}>
            <div style={headingStyle}>Email Draft</div>
            {commDraft.email_draft.subject && (
              <div style={{ ...cardBg, marginBottom: '0.5rem' }}><span className="text-muted">Subject: </span><strong>{commDraft.email_draft.subject}</strong></div>
            )}
            {commDraft.email_draft.body && (
              <div style={{ ...cardBg, whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{commDraft.email_draft.body}</div>
            )}
          </div>
        )}

        {/* Data Sources Status */}
        <div style={sectionStyle}>
          <div style={headingStyle}>Data Sources</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.5rem' }}>
            {[
              { label: 'Sheets', key: 'google_sheets_mcp_status' },
              { label: 'Calendar', key: 'calendar_mcp_status' },
              { label: 'News', key: 'news_mcp_status' },
              { label: 'Suppliers', key: 'supplier_intelligence_mcp_status' },
              { label: 'Risk Registry', key: 'risk_registry_mcp_status' },
            ].map(({ label, key }) => {
              const status = mcpData[key] || 'unknown';
              const color = status === 'success' ? 'var(--status-success)' : status === 'degraded' ? 'var(--status-warning)' : status === 'error' ? 'var(--status-error)' : 'var(--text-muted)';
              return (
                <div key={key} style={{ ...cardBg, textAlign: 'center' }}>
                  <div className="text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.2rem' }}>{label}</div>
                  <div style={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '0.8rem', color }}>{status}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Audit Trail / Execution Logs */}
        {auditTrail && auditTrail.length > 0 && (
          <div style={sectionStyle}>
            <div style={headingStyle}>Multi-Agent Execution Trace</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {auditTrail.map((log, idx) => (
                <div key={idx} style={{ ...cardBg, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{ 
                      display: 'inline-block', 
                      width: '8px', 
                      height: '8px', 
                      borderRadius: '50%', 
                      background: log.status === 'success' ? 'var(--status-success)' : 'var(--status-warning)' 
                    }}></span>
                    <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>
                      {log.step ? log.step.replace(/_/g, ' ') : 'Step'}
                    </span>
                  </div>
                  <div className="text-secondary" style={{ fontSize: '0.82rem' }}>
                    <span className="text-muted">Duration: </span>{log.duration_ms}ms
                    <span style={{ marginLeft: '1rem', opacity: 0.6 }}>{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="animate-fade-in mt-8">
      <h2 className="mb-4 text-gradient" style={{ fontSize: '1.75rem' }}>Risk Intelligence Dashboard</h2>
      
      <div className="grid-3">
        {renderMetric('Overall Risk', 'overall_risk_score', <ShieldAlert size={20} />)}
        {renderMetric('Business Health', 'business_health_score', <TrendingUp size={20} />, true)}
        {renderMetric('Inventory Risk', 'inventory_risk', <Box size={20} />)}
        {renderMetric('Finance Risk', 'finance_risk', <Zap size={20} />)}
        {renderMetric('Supplier Risk', 'supplier_risk', <AlertTriangle size={20} />)}
      </div>

      {reports && reports.length > 0 && (
        <div className="mt-8">
          <h3 className="mb-4" style={{ fontSize: '1.25rem' }}>Recent Reports</h3>
          <div className="flex-col gap-3">
            {reports.slice(0, 5).map((r, i) => {
              const isExpanded = expandedReport === i;
              return (
                <div key={i} className="glass-panel" style={{ overflow: 'hidden' }}>
                  <div
                    style={{ padding: '1rem 1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                    onClick={() => setExpandedReport(isExpanded ? null : i)}
                  >
                    <div>
                      <div style={{ fontWeight: 500 }}>{r.report_type || 'Analysis Report'}</div>
                      <div className="text-muted" style={{ fontSize: '0.85rem' }}>{new Date(r.generated_at).toLocaleString()}</div>
                    </div>
                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: '0.85rem', padding: '0.4rem 1rem' }}
                      onClick={(e) => { e.stopPropagation(); setExpandedReport(isExpanded ? null : i); }}
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      {isExpanded ? 'Hide Details' : 'View Details'}
                    </button>
                  </div>
                  {isExpanded && (
                    <div style={{ padding: '0 1.5rem 1.5rem', borderTop: '1px solid var(--border-light)', marginTop: '0.5rem', paddingTop: '1rem' }}>
                      {renderReportContent(r)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
