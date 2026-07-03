const API_BASE = import.meta.env.VITE_API_BASE || 'https://business-guardian-ai-awhy.onrender.com';
const API_KEY = import.meta.env.VITE_GOOGLE_API_KEY || '';

const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
};

export const api = {
  analyze: async (data) => {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  
  approve: async (run_id, approval_status) => {
    const res = await fetch(`${API_BASE}/analyze/approve`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ run_id, approval_status }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  
  getReports: async (business_id) => {
    const res = await fetch(`${API_BASE}/reports?business_id=${business_id}`, {
      headers
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  
  getHistory: async (business_id) => {
    const res = await fetch(`${API_BASE}/history?business_id=${business_id}`, {
      headers
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
};
