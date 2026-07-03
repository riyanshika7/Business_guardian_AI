import React from 'react';
import { Target, ArrowRight } from 'lucide-react';

export default function ActionItems({ recommendations }) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="animate-slide-up mt-8">
      <h3 className="section-title mb-4" style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Target size={20} className="text-accent-blue" />
        Prioritized Action Items
      </h3>
      <div className="flex-col gap-3">
        {recommendations.map((rec, i) => (
          <div key={i} className="glass-panel" style={{ padding: '1rem 1.5rem', display: 'flex', alignItems: 'flex-start', gap: '1rem', borderLeft: '4px solid var(--accent-purple)' }}>
            <div style={{ marginTop: '0.2rem' }}>
              <ArrowRight size={18} className="text-accent-purple" />
            </div>
            <div>
              <p style={{ fontWeight: 500, marginBottom: '0.25rem' }}>{rec.action_title}</p>
              {rec.action_description && (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{rec.action_description}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
