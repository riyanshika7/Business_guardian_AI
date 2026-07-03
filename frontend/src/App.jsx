import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import ActionItems from './components/ActionItems';
import DraftViewer from './components/DraftViewer';
import { ShieldAlert, Check, X, Activity, AlertTriangle, TrendingUp, Box, Zap, Loader } from 'lucide-react';
import { api } from './api';
import heroImage from './assets/hero.png';

function ScoreCards({ scores, criticalRisks, riskTrend }) {
  if (!scores) return null;

  const getScoreColor = (score, reverse = false) => {
    if (score === null || score === undefined) return 'var(--text-muted)';
    if (reverse) {
      if (score >= 70) return 'var(--status-success)';
      if (score >= 40) return 'var(--status-warning)';
      return 'var(--status-error)';
    }
    if (score >= 70) return 'var(--status-error)';
    if (score >= 40) return 'var(--status-warning)';
    return 'var(--status-success)';
  };

  const cards = [
    { label: 'Business Health', value: scores.business_health_score, icon: <TrendingUp size={20} />, reverse: true },
    { label: 'Overall Risk', value: scores.business_risk_score, icon: <ShieldAlert size={20} /> },
    { label: 'Inventory Risk', value: scores.inventory_risk, icon: <Box size={20} /> },
    { label: 'Finance Risk', value: scores.finance_risk, icon: <Zap size={20} /> },
    { label: 'Supplier Risk', value: scores.supplier_risk, icon: <AlertTriangle size={20} /> },
    { label: 'Compliance Risk', value: scores.compliance_risk, icon: <Activity size={20} /> },
  ];

  return (
    <div className="animate-slide-up">
      <h2 className="mb-4 text-gradient" style={{ fontSize: '1.5rem' }}>Live Analysis Scores</h2>
      {riskTrend && (
        <p className="text-secondary mb-4" style={{ fontSize: '0.9rem' }}>
          Risk Trend: <span style={{ fontWeight: 600, textTransform: 'uppercase', color: riskTrend === 'improving' ? 'var(--status-success)' : riskTrend === 'worsening' ? 'var(--status-error)' : 'var(--status-warning)' }}>{riskTrend}</span>
        </p>
      )}
      <div className="grid-3">
        {cards.map(({ label, value, icon, reverse }) => (
          <div key={label} className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div className="flex items-center justify-between text-muted">
              <span style={{ fontSize: '0.85rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
              {icon}
            </div>
            <span style={{ fontSize: '2.5rem', fontWeight: 700, color: getScoreColor(value, reverse) }}>
              {value !== null && value !== undefined ? value : '—'}
            </span>
          </div>
        ))}
      </div>

      {criticalRisks && criticalRisks.length > 0 && (
        <div className="mt-4">
          <h3 className="text-error mb-4" style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={18} /> Critical Risks Identified
          </h3>
          <div className="flex-col gap-2">
            {criticalRisks.map((r, i) => (
              <div key={i} className="glass-panel" style={{ padding: '0.75rem 1.25rem', borderLeft: '4px solid var(--status-error)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{r.domain}</span>
                <span style={{ color: getScoreColor(r.score), fontWeight: 700 }}>{r.score}/100 <span className="text-muted" style={{ fontWeight: 400, fontSize: '0.8rem' }}>({r.severity})</span></span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function HitlInlineReview({ onApprove, onReject, isRunning }) {
  return (
    <div className="animate-slide-up mt-8 glass-panel" style={{ padding: '2rem', borderLeft: '4px solid var(--status-warning)' }}>
      <div className="flex items-center gap-4 mb-4">
        <ShieldAlert size={28} style={{ color: 'var(--status-warning)' }} />
        <div>
          <h3 style={{ fontSize: '1.25rem', color: 'var(--text-primary)' }}>Human Review Required</h3>
          <p className="text-secondary" style={{ fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Review the scores, action items, and communication drafts above. Then approve or reject distribution.
          </p>
        </div>
      </div>
      <div className="flex gap-4 mt-4">
        <button
          className="btn"
          onClick={onReject}
          disabled={isRunning}
          style={{ flex: 1, border: '1px solid var(--status-error)', color: 'var(--status-error)', background: 'rgba(239, 68, 68, 0.1)' }}
        >
          {isRunning ? <Loader size={18} className="spin" /> : <X size={18} />} Reject &amp; Purge
        </button>
        <button
          className="btn"
          onClick={onApprove}
          disabled={isRunning}
          style={{ flex: 1, border: '1px solid var(--status-success)', color: 'var(--status-success)', background: 'rgba(16, 185, 129, 0.1)' }}
        >
          {isRunning ? <Loader size={18} className="spin" /> : <Check size={18} />} Approve Release
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [formData, setFormData] = useState({
    business_id: 'BIZ-101',
    business_name: 'Apex Enterprises Ltd',
    business_type: 'retail',
    period_days: 30,
    analysis_window_days: 30,
    communication_type: 'both',
    recipient_name: 'Johnathan Owner'
  });

  const [history, setHistory] = useState([]);
  const [reports, setReports] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [stage, setStage] = useState('idle'); // idle | pending_hitl | completed | error
  const [activeRun, setActiveRun] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [page, setPage] = useState('landing'); // landing | config | dashboard

  const fetchDashboardData = async () => {
    try {
      const hist = await api.getHistory(formData.business_id);
      const reps = await api.getReports(formData.business_id);
      setHistory(hist);
      setReports(reps);
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [formData.business_id]);

  const navigateToPage = (targetPage) => {
    setPage(targetPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleAnalyze = async () => {
    setIsRunning(true);
    setStage('idle');
    setActiveRun(null);
    setErrorMsg(null);
    try {
      const res = await api.analyze(formData);
      setActiveRun(res);

      if (res.system_status === 'awaiting_human_approval') {
        setStage('pending_hitl');
        await fetchDashboardData();
        navigateToPage('dashboard');
      } else if (res.system_status === 'error') {
        setStage('error');
        setErrorMsg(res.error?.error_message || 'Unknown pipeline error');
      } else {
        setStage('completed');
        await fetchDashboardData();
        navigateToPage('dashboard');
      }
    } catch (err) {
      setStage('error');
      setErrorMsg(err.message);
    } finally {
      setIsRunning(false);
    }
  };

  const handleApprove = async (isApproved) => {
    setIsRunning(true);
    try {
      const res = await api.approve(activeRun.run_id, isApproved ? 'approved' : 'rejected');
      if (res.system_status === 'error') {
        setStage('error');
        setErrorMsg(res.error?.error_message || 'Unknown pipeline error');
      } else {
        setStage('completed');
        setActiveRun(null);
        fetchDashboardData();
      }
    } catch (err) {
      setStage('error');
      setErrorMsg(err.message);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="app-layout">
      <main className="main-content">
        {page === 'landing' && (
          <section className="landing-hero glass-panel">
            <div className="hero-copy">
              <span className="hero-badge">Business Guardian AI</span>
              <h1>Protect your business with operational risk intelligence.</h1>
              <p>Monitor your business, detect risks, receive intelligent recommendations, and grow with confidence.</p>
              <div className="hero-buttons">
                <button className="btn btn-primary hero-button" onClick={() => navigateToPage('config')}>Get Started</button>
                <button className="btn btn-secondary hero-button" onClick={() => navigateToPage('dashboard')}>Watch Demo</button>
              </div>
              <div className="hero-highlights">
                <div className="hero-highlight">🤖 <strong>Coordinated Multi-Agent Orchestration</strong> – Coordinates specialized AI agents evaluating inventory, finance, suppliers, and compliance in real-time.</div>
                <div className="hero-highlight">🔍 <strong>Predictive Risk Intelligence</strong> – Automatically flags potential stockouts, delayed shipments, and upcoming regulatory or tax deadlines before they impact you.</div>
                <div className="hero-highlight">🛡️ <strong>Human-in-the-Loop Safeguards</strong> – Implements secure approval gates, allowing you to review, edit, or reject reports and email drafts before dispatch.</div>
              </div>
              <p className="hero-footer">Trusted by startups & growing businesses.</p>
            </div>

            <div className="hero-panel">
              <div className="hero-panel-content">
                <img src={heroImage} alt="Business Guardian AI landing preview" />
              </div>
            </div>
          </section>
        )}

        {page === 'config' && (
          <section className="config-page">
            <div className="page-header">
              <div className="page-action-row">
                <div>
                  <p className="page-step">01 · Business Details</p>
                  <h1>Fill Your Business Details Here!</h1>
                  <p>Complete the form to run analysis and continue to the dashboard.</p>
                </div>
                <button className="btn btn-secondary" onClick={() => navigateToPage('landing')}>Back to Landing</button>
              </div>
            </div>
            {stage === 'error' && (
              <div className="alert alert-error" style={{ width: '100%', maxWidth: '1120px' }}>
                <strong>Analysis failed:</strong> {errorMsg}
              </div>
            )}
            <div className="config-grid">
              <Sidebar layout="page" formData={formData} setFormData={setFormData} onSubmit={handleAnalyze} isRunning={isRunning} />
            </div>
          </section>
        )}

        {page === 'dashboard' && (
          <section className="dashboard-page">
            <div className="page-header">
              <div className="page-action-row">
                <div>
                  <p className="page-step">03 · Dashboard</p>
                  <h1>Dashboard</h1>
                  <p>Review risk scores, action items, and communication drafts using the analysis engine.</p>
                </div>
                <button className="btn btn-secondary" onClick={() => navigateToPage('config')}>Back to Form</button>
              </div>
            </div>

            {stage === 'error' && (
              <div className="alert alert-error">
                <strong>System Error:</strong> {errorMsg}
              </div>
            )}

            {stage === 'completed' && (
              <div className="alert alert-success">
                <strong>Analysis Pipeline Completed.</strong> Risk scores and reports have been updated in the database.
              </div>
            )}

            {activeRun && (
              <div className="mb-8">
                <ScoreCards 
                  scores={activeRun.scores} 
                  criticalRisks={activeRun.critical_risks}
                  riskTrend={activeRun.risk_trend}
                />
                <ActionItems recommendations={activeRun.top_recommendations} />
                <DraftViewer communication_draft={activeRun.communication_draft} />

                {stage === 'pending_hitl' && (
                  <HitlInlineReview 
                    onApprove={() => handleApprove(true)} 
                    onReject={() => handleApprove(false)}
                    isRunning={isRunning}
                  />
                )}
              </div>
            )}

            <section id="dashboard-section" className="dashboard-section">
              <Dashboard history={history} reports={reports} />
            </section>
          </section>
        )}
      </main>
    </div>
  );
}
