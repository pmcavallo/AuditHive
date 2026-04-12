import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

const RISK_STYLES = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-green-100 text-green-800',
};

export default function Templates() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [policyName, setPolicyName] = useState('');
  const [customizations, setCustomizations] = useState('{}');
  const [applyError, setApplyError] = useState('');
  const [applying, setApplying] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.getTemplates().then(async (r) => {
      if (r) setTemplates((await r.json()).templates);
      setLoading(false);
    });
  }, []);

  async function handleSelect(id) {
    if (selected === id) {
      setSelected(null);
      setDetail(null);
      return;
    }
    setSelected(id);
    const r = await api.getTemplate(id);
    if (r) setDetail(await r.json());
    const t = templates.find((t) => t.id === id);
    setPolicyName(t?.name || '');
    setCustomizations('{}');
    setApplyError('');
  }

  async function handleApply() {
    setApplyError('');
    setApplying(true);
    try {
      const body = { name: policyName || undefined, customizations: JSON.parse(customizations) };
      const r = await api.applyTemplate(selected, body);
      if (r && r.ok) {
        navigate('/policies');
      } else {
        const data = await r?.json();
        setApplyError(data?.detail || 'Failed to apply template.');
      }
    } catch {
      setApplyError('Invalid customization JSON.');
    } finally {
      setApplying(false);
    }
  }

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Policy Templates</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {templates.map((t) => (
          <div
            key={t.id}
            className={`bg-white rounded-lg shadow p-6 cursor-pointer border-2 transition-colors ${
              selected === t.id ? 'border-blue-500' : 'border-transparent hover:border-gray-200'
            }`}
            onClick={() => handleSelect(t.id)}
          >
            <div className="flex items-start justify-between mb-3">
              <h3 className="text-lg font-semibold text-gray-900">{t.name}</h3>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${RISK_STYLES[t.risk_level] || RISK_STYLES.medium}`}>
                {t.risk_level}
              </span>
            </div>
            <p className="text-sm text-gray-600 line-clamp-2 mb-3">{t.description}</p>
            <p className="text-xs text-gray-400">Use case: {t.use_case}</p>
            {t.regulatory_grounding?.length > 0 && (
              <details className="mt-3">
                <summary className="text-xs text-blue-600 cursor-pointer hover:underline">
                  Regulatory grounding ({t.regulatory_grounding.length})
                </summary>
                <ul className="mt-1 text-xs text-gray-500 space-y-0.5 pl-4 list-disc">
                  {t.regulatory_grounding.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))}
      </div>

      {/* Apply panel */}
      {selected && detail && (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h3 className="text-lg font-semibold text-gray-800">Apply: {detail.name}</h3>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Policy Name</label>
            <input
              type="text"
              value={policyName}
              onChange={(e) => setPolicyName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Customizations (JSON, optional)
            </label>
            <textarea
              value={customizations}
              onChange={(e) => setCustomizations(e.target.value)}
              rows={6}
              className="w-full font-mono text-xs border border-gray-300 rounded-md p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <details>
            <summary className="text-sm text-blue-600 cursor-pointer hover:underline">
              View template config
            </summary>
            <pre className="mt-2 bg-gray-50 rounded p-3 text-xs overflow-auto max-h-64">
              {JSON.stringify(detail.config, null, 2)}
            </pre>
          </details>

          {applyError && <p className="text-sm text-red-600">{applyError}</p>}

          <button
            onClick={handleApply}
            disabled={applying}
            className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {applying ? 'Applying...' : 'Apply Template'}
          </button>
        </div>
      )}
    </div>
  );
}
