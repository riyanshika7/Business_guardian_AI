import React from 'react';
import { ShieldAlert, Check, X } from 'lucide-react';

export default function HitlReviewModal({ onApprove, onReject }) {
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="flex items-center gap-4 mb-6 text-warning">
          <ShieldAlert size={36} />
          <h2 style={{ fontSize: '1.5rem', color: 'var(--text-primary)' }}>Human Review Required</h2>
        </div>
        
        <p className="text-secondary mb-8">
          The AI pipeline has flagged this analysis run for manual review due to a low confidence score or critical validation failure in the communication drafts. 
          <br /><br />
          Please review the generated drafts and risk scores. Do you approve the distribution of these reports?
        </p>

        <div className="flex justify-between gap-4 mt-8 pt-6" style={{ borderTop: '1px solid var(--border-light)' }}>
          <button className="btn" onClick={onReject} style={{ flex: 1, border: '1px solid var(--status-error)', color: 'var(--status-error)', background: 'rgba(239, 68, 68, 0.1)' }}>
            <X size={18} /> Reject & Purge
          </button>
          <button className="btn" onClick={onApprove} style={{ flex: 1, border: '1px solid var(--status-success)', color: 'var(--status-success)', background: 'rgba(16, 185, 129, 0.1)' }}>
            <Check size={18} /> Approve Release
          </button>
        </div>
      </div>
    </div>
  );
}
