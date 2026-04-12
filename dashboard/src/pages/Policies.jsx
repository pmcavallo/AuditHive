import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

export default function Policies() {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [customJson, setCustomJson] = useState('{\n  "name": "",\n  "config": {}\n}');
  const [createError, setCreateError] = useState('');
  const navigate = useNavigate();

  function loadPolicies() {
    setLoading(true);
    api.getPolicies().then(async (r) => {
      if (r) setPolicies((await r.json()).policies);
      setLoading(false);
    });
  }

  useEffect(() => { loadPolicies(); }, []);

  async function handleDeactivate(id) {
    await api.deletePolicy(id);
    loadPolicies();
  }

  async function handleCreate() {
    setCreateError('');
    try {
      const body = JSON.parse(customJson);
      const r = await api.createPolicy(body);
      if (r && r.ok) {
        setShowCreate(false);
        loadPolicies();
      } else {
        const data = await r?.json();
        setCreateError(data?.detail || 'Failed to create policy.');
      }
    } catch {
      setCreateError('Invalid JSON.');
    }
  }

  function enabledChecks(config) {
    let count = 0;
    const flat = config?.pre_call || config;
    for (const val of Object.values(flat)) {
      if (val && typeof val === 'object' && val.enabled) count++;
    }
    return count;
  }

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Policies</h2>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/templates')}
            className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Create from Template
          </button>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="px-4 py-2 text-sm font-medium border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Create Custom
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="bg-white rounded-lg shadow p-6 space-y-3">
          <h3 className="text-lg font-semibold text-gray-800">Custom Policy (JSON)</h3>
          <textarea
            value={customJson}
            onChange={(e) => setCustomJson(e.target.value)}
            rows={10}
            className="w-full font-mono text-xs border border-gray-300 rounded-md p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {createError && <p className="text-sm text-red-600">{createError}</p>}
          <button onClick={handleCreate} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">
            Create
          </button>
        </div>
      )}

      {policies.length === 0 ? (
        <p className="text-gray-500 text-center py-10">No active policies. Create one from a template to get started.</p>
      ) : (
        <div className="space-y-4">
          {policies.map((p) => (
            <div key={p.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">{p.name}</h3>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {p.template_id ? `From template: ${p.template_id}` : 'Custom policy'}
                    {' \u00B7 '}{enabledChecks(p.config)} checks enabled
                    {' \u00B7 '}Created {new Date(p.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setExpanded(expanded === p.id ? null : p.id)}
                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                  >
                    {expanded === p.id ? 'Hide Config' : 'View Config'}
                  </button>
                  <button
                    onClick={() => handleDeactivate(p.id)}
                    className="px-3 py-1 text-sm border border-red-300 text-red-600 rounded hover:bg-red-50"
                  >
                    Deactivate
                  </button>
                </div>
              </div>
              {expanded === p.id && (
                <pre className="mt-4 bg-gray-50 rounded p-4 text-xs overflow-auto max-h-80">
                  {JSON.stringify(p.config, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
