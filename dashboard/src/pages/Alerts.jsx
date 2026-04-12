import { useEffect, useState } from 'react';
import { api } from '../api';

export default function Alerts() {
  const [config, setConfig] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [form, setForm] = useState({
    on_block: true, on_flag: false, on_gap_detected: true, on_coverage_change: false,
    email_addresses: '', webhook_urls: '',
  });

  useEffect(() => {
    Promise.all([
      api.getAlertConfig().then(async (r) => {
        if (r && r.ok) {
          const c = await r.json();
          setConfig(c);
          setForm({
            on_block: c.on_block, on_flag: c.on_flag,
            on_gap_detected: c.on_gap_detected, on_coverage_change: c.on_coverage_change,
            email_addresses: (c.email_addresses || []).join(', '),
            webhook_urls: (c.webhook_urls || []).join('\n'),
          });
        }
      }),
      api.getAlertHistory({ limit: 20 }).then(async (r) => {
        if (r && r.ok) setHistory((await r.json()).alerts);
      }),
    ]).finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    const data = {
      on_block: form.on_block, on_flag: form.on_flag,
      on_gap_detected: form.on_gap_detected, on_coverage_change: form.on_coverage_change,
      email_addresses: form.email_addresses.split(',').map((s) => s.trim()).filter(Boolean),
      webhook_urls: form.webhook_urls.split('\n').map((s) => s.trim()).filter(Boolean),
    };
    await api.saveAlertConfig(data);
    setSaving(false);
  }

  async function handleTest() {
    setTesting(true);
    await api.testAlert();
    setTesting(false);
    const r = await api.getAlertHistory({ limit: 20 });
    if (r && r.ok) setHistory((await r.json()).alerts);
  }

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Alerts</h2>

      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-800">Configuration</h3>
        <div className="space-y-2">
          {[['on_block', 'On policy block'], ['on_flag', 'On policy flag'], ['on_gap_detected', 'On gap detected'], ['on_coverage_change', 'On coverage change']].map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.checked })} />
              {label}
            </label>
          ))}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email addresses (comma-separated)</label>
          <input type="text" value={form.email_addresses} onChange={(e) => setForm({ ...form, email_addresses: e.target.value })}
            className="w-full border rounded px-3 py-2 text-sm" placeholder="ops@company.com, compliance@company.com" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URLs (one per line)</label>
          <textarea value={form.webhook_urls} onChange={(e) => setForm({ ...form, webhook_urls: e.target.value })}
            rows={3} className="w-full border rounded px-3 py-2 text-sm font-mono" placeholder="https://hooks.slack.com/..." />
        </div>
        <div className="flex gap-2">
          <button onClick={handleSave} disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm font-medium">
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
          <button onClick={handleTest} disabled={testing}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 text-sm font-medium">
            {testing ? 'Sending...' : 'Send Test Alert'}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b"><h3 className="text-lg font-semibold text-gray-800">Alert History</h3></div>
        {history.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No alerts sent yet.</p>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Channels</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {history.map((a) => (
                <tr key={a.id}>
                  <td className="px-6 py-4 text-sm">{new Date(a.created_at).toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm">{a.trigger_type}</td>
                  <td className="px-6 py-4 text-sm">{(a.channels_sent || []).join(', ') || '-'}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${a.status === 'sent' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {a.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
