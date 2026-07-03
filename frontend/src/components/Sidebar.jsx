import React from 'react';
import { Play, Activity, Clock } from 'lucide-react';

export default function Sidebar({ formData, setFormData, onSubmit, isRunning }) {
  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? Number(value) : value
    }));
  };

  return (
    <aside id="config-form" className="sidebar">
      <div className="flex items-center gap-3 mb-8">
        <Activity size={32} className="text-accent-blue" />
        <h2 className="text-gradient" style={{ fontSize: '1.25rem' }}>Guardian AI</h2>
      </div>

      <div className="flex-col gap-4 mt-4" style={{ flex: 1 }}>
        <h3 className="text-muted" style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '1rem' }}>Configuration</h3>
        
        <div className="input-group">
          <label className="input-label">Business ID</label>
          <input className="input-field" name="business_id" value={formData.business_id} onChange={handleChange} />
        </div>
        
        <div className="input-group">
          <label className="input-label">Business Name</label>
          <input className="input-field" name="business_name" value={formData.business_name} onChange={handleChange} />
        </div>

        <div className="input-group">
          <label className="input-label">Business Type</label>
          <select className="input-field select-field" name="business_type" value={formData.business_type} onChange={handleChange}>
            <option value="retail">Retail</option>
            <option value="agriculture">Agriculture</option>
            <option value="ecommerce">E-Commerce</option>
          </select>
        </div>

        <div className="flex items-center gap-3">
          <div className="input-group" style={{ flex: 1 }}>
            <label className="input-label">Period (Days)</label>
            <input className="input-field" type="number" name="period_days" value={formData.period_days} onChange={handleChange} />
          </div>
          <div className="input-group" style={{ flex: 1 }}>
            <label className="input-label">Window (Days)</label>
            <input className="input-field" type="number" name="analysis_window_days" value={formData.analysis_window_days} onChange={handleChange} />
          </div>
        </div>

        <div className="input-group">
          <label className="input-label">Communication</label>
          <select className="input-field select-field" name="communication_type" value={formData.communication_type} onChange={handleChange}>
            <option value="both">Both (Email + Report)</option>
            <option value="email">Email Only</option>
            <option value="report">Report Only</option>
          </select>
        </div>
      </div>

      <button 
        className="btn btn-primary" 
        onClick={onSubmit}
        disabled={isRunning}
        style={{ width: '100%', marginTop: 'auto' }}
      >
        {isRunning ? <Clock size={18} className="animate-spin" /> : <Play size={18} />}
        <span>{isRunning ? 'Analyzing...' : 'Run Analysis'}</span>
      </button>
    </aside>
  );
}
