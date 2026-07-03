import React from 'react';
import { FileText } from 'lucide-react';

export default function DraftViewer({ communication_draft }) {
  if (!communication_draft) return null;

  return (
    <div className="animate-slide-up mt-8">
      <h3 className="section-title mb-4" style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <FileText size={20} className="text-accent-blue" />
        Communication Draft
      </h3>
      <div className="glass-panel" style={{ padding: '1.5rem', background: 'rgba(255, 255, 255, 0.02)' }}>
        {Object.entries(communication_draft).map(([key, value]) => {
          if (!value || typeof value === 'boolean') return null;
          if (['approval_required', 'approval_status', 'status', 'timestamp', 'agent'].includes(key)) return null;
          
          if (typeof value === 'string') {
            return (
              <div key={key} style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ textTransform: 'capitalize', color: 'var(--text-secondary)', fontSize: '0.85rem', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
                  {key.replace(/_/g, ' ')}
                </h4>
                <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', color: 'var(--text-primary)', background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: 'var(--radius-sm)' }}>
                  {value}
                </div>
              </div>
            );
          }

          if (typeof value === 'object') {
            return (
              <div key={key} style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ textTransform: 'capitalize', color: 'var(--text-secondary)', fontSize: '0.85rem', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
                  {key.replace(/_/g, ' ')}
                </h4>
                <div style={{ fontSize: '0.95rem', color: 'var(--text-primary)', background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: 'var(--radius-sm)' }}>
                  {Object.entries(value).map(([subKey, subValue]) => (
                    <div key={subKey} style={{ marginBottom: '0.75rem' }}>
                      <span style={{ color: 'var(--text-secondary)', fontWeight: '600', textTransform: 'capitalize', marginRight: '0.5rem' }}>
                        {subKey.replace(/_/g, ' ')}:
                      </span>
                      <span style={{ whiteSpace: 'pre-wrap' }}>
                        {Array.isArray(subValue) ? subValue.join(', ') : String(subValue)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          }
          return null;
        })}
      </div>
    </div>
  );
}
