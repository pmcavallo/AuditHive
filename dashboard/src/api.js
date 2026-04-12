import {
  IS_DEMO,
  demoStats,
  demoAuditLogs,
  demoPolicies,
  demoTemplates,
  demoProfile,
  demoAssessment,
  demoGaps,
  demoExaminerReport,
  demoReports,
  demoRegulatoryImpact,
  demoTimeline,
  demoAlertConfig,
  demoAlertHistory,
} from './demo-data';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function demoResponse(data) {
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(data), text: () => Promise.resolve(JSON.stringify(data)) });
}

function filterDemoLogs(params) {
  let logs = [...demoAuditLogs];
  const status = params?.status;
  if (status) logs = logs.filter((l) => l.status === status);
  const offset = parseInt(params?.offset || '0', 10);
  const limit = parseInt(params?.limit || '20', 10);
  return { logs: logs.slice(offset, offset + limit), total: logs.length, limit, offset };
}

async function apiCall(path, options = {}) {
  const apiKey = localStorage.getItem('audithive_api_key');
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
      ...options.headers,
    },
  });
  if (response.status === 401) {
    localStorage.removeItem('audithive_api_key');
    window.location.href = '/login';
    return;
  }
  return response;
}

export { IS_DEMO };

export const api = {
  // Auth
  checkHealth: (key) =>
    IS_DEMO
      ? demoResponse({ status: 'healthy', customer_id: 'demo' })
      : fetch(`${API_BASE}/v1/health`, { headers: { Authorization: `Bearer ${key}` } }),

  // Audit
  getAuditLogs: (params) => IS_DEMO ? demoResponse(filterDemoLogs(params)) : apiCall(`/v1/audit-logs?${new URLSearchParams(params)}`),
  getAuditLog: (id) => IS_DEMO ? demoResponse(demoAuditLogs.find((l) => l.id === id) || demoAuditLogs[0]) : apiCall(`/v1/audit-logs/${id}`),
  getAuditStats: (days = 7) => IS_DEMO ? demoResponse(demoStats) : apiCall(`/v1/audit-logs/stats?days=${days}`),

  // Policies
  getPolicies: () => IS_DEMO ? demoResponse({ policies: demoPolicies }) : apiCall('/v1/policies'),
  createPolicy: (data) => IS_DEMO ? demoResponse({ id: 'new', ...data }) : apiCall('/v1/policies', { method: 'POST', body: JSON.stringify(data) }),
  deletePolicy: (id) => IS_DEMO ? demoResponse({ status: 'deactivated' }) : apiCall(`/v1/policies/${id}`, { method: 'DELETE' }),

  // Templates
  getTemplates: () => IS_DEMO ? demoResponse({ templates: demoTemplates }) : apiCall('/v1/templates'),
  getTemplate: (id) => IS_DEMO ? demoResponse({ ...demoTemplates.find((t) => t.id === id), config: {} }) : apiCall(`/v1/templates/${id}`),
  applyTemplate: (id, data) => IS_DEMO ? demoResponse({ policy_id: 'new', template_id: id, ...data, message: 'Policy created from template.' }) : apiCall(`/v1/templates/${id}/apply`, { method: 'POST', body: JSON.stringify(data) }),

  // Profile & Assessment
  getProfile: () => IS_DEMO ? demoResponse(demoProfile) : apiCall('/v1/profile'),
  saveProfile: (data) => IS_DEMO ? demoResponse({ profile_id: 'demo', ...data }) : apiCall('/v1/profile', { method: 'POST', body: JSON.stringify(data) }),
  getAssessment: () => IS_DEMO ? demoResponse(demoAssessment) : apiCall('/v1/assessment'),
  getGaps: () => IS_DEMO ? demoResponse(demoGaps) : apiCall('/v1/assessment/gaps'),
  submitFourQuestions: (data) => IS_DEMO ? demoResponse({ maturity_level: 'developing', maturity_score: 3, questions: demoAssessment.four_questions, maturity_breakdown: '3/4 answered.' }) : apiCall('/v1/assessment/four-questions', { method: 'POST', body: JSON.stringify(data) }),

  // Regulatory
  getRegulatoryUpdates: () => IS_DEMO ? demoResponse({ updates: demoRegulatoryImpact.impacts.map((i) => i.regulatory_update) }) : apiCall('/v1/regulatory/updates'),
  getRegulatoryImpact: (params) => IS_DEMO ? demoResponse(demoRegulatoryImpact) : apiCall(`/v1/regulatory/impact?${new URLSearchParams(params || {})}`),
  getRegulatoryTimeline: (days) => IS_DEMO ? demoResponse({ timeline: demoTimeline }) : apiCall(`/v1/regulatory/timeline?days_ahead=${days || 180}`),
  acknowledgeImpact: (id) => IS_DEMO ? demoResponse({ acknowledged: true }) : apiCall(`/v1/regulatory/impact/${id}/acknowledge`, { method: 'POST' }),

  // Reports
  generateReport: (data) => IS_DEMO ? demoResponse({ report_id: 'rpt-demo', status: 'generated', coverage_score: 67, maturity_level: 'developing', findings_count: 3, download_url: '#' }) : apiCall('/v1/reports/generate', { method: 'POST', body: JSON.stringify(data) }),
  getReports: () => IS_DEMO ? demoResponse({ reports: demoReports }) : apiCall('/v1/reports'),
  downloadReport: (id) => IS_DEMO ? demoResponse('<h1>Demo Report</h1><p>This is a demo report preview.</p>') : apiCall(`/v1/reports/${id}/download`),
  weeklyDigest: () => IS_DEMO ? demoResponse(demoExaminerReport) : apiCall('/v1/reports/weekly-digest', { method: 'POST' }),

  // Alerts
  getAlertConfig: () => IS_DEMO ? demoResponse(demoAlertConfig) : apiCall('/v1/alerts/config'),
  saveAlertConfig: (data) => IS_DEMO ? demoResponse({ ...demoAlertConfig, ...data }) : apiCall('/v1/alerts/config', { method: 'POST', body: JSON.stringify(data) }),
  getAlertHistory: (params) => IS_DEMO ? demoResponse({ alerts: demoAlertHistory, total: demoAlertHistory.length }) : apiCall(`/v1/alerts/history?${new URLSearchParams(params)}`),
  testAlert: () => IS_DEMO ? demoResponse({ status: 'sent' }) : apiCall('/v1/alerts/test', { method: 'POST' }),

  // Account
  exportAccount: () => IS_DEMO ? demoResponse({ export_date: new Date().toISOString(), customer: { name: 'Demo' } }) : apiCall('/v1/account/export'),
  deleteAccount: () => IS_DEMO ? demoResponse({ deleted: false, message: 'Delete is disabled in demo mode.' }) : apiCall('/v1/account', { method: 'DELETE', body: JSON.stringify({ confirm: true }) }),
};
