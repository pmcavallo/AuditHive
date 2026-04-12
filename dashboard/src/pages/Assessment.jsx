import { useEffect, useState } from 'react';
import { api } from '../api';

const MATURITY_STYLES = {
  mature: 'bg-green-100 text-green-800',
  developing: 'bg-yellow-100 text-yellow-800',
  immature: 'bg-orange-100 text-orange-800',
  ungoverned: 'bg-red-100 text-red-800',
};

export default function Assessment() {
  const [profile, setProfile] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [gaps, setGaps] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [form, setForm] = useState({ ai_use_cases: [], audience_types: [], industry: '', jurisdictions: [] });
  const [fourQ, setFourQ] = useState({ purpose: '', working: '', failure: '', accountability: '' });
  const [fourQResult, setFourQResult] = useState(null);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    setLoading(true);
    const pRes = await api.getProfile();
    if (pRes && pRes.ok) {
      const p = await pRes.json();
      setProfile(p);
      const [aRes, gRes] = await Promise.all([api.getAssessment(), api.getGaps()]);
      if (aRes && aRes.ok) setAssessment(await aRes.json());
      if (gRes && gRes.ok) setGaps(await gRes.json());
    } else {
      setShowOnboarding(true);
    }
    setLoading(false);
  }

  async function handleOnboarding(e) {
    e.preventDefault();
    const r = await api.saveProfile(form);
    if (r && r.ok) {
      setShowOnboarding(false);
      loadData();
    }
  }

  function toggle(field, value) {
    setForm((f) => ({
      ...f,
      [field]: f[field].includes(value) ? f[field].filter((v) => v !== value) : [...f[field], value],
    }));
  }

  async function handleFourQuestions(e) {
    e.preventDefault();
    const body = {};
    for (const [k, v] of Object.entries(fourQ)) { if (v) body[k] = v; }
    const r = await api.submitFourQuestions(body);
    if (r && r.ok) setFourQResult(await r.json());
  }

  if (loading) return <p className="text-gray-500">Loading...</p>;

  if (showOnboarding) {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Governance Assessment</h2>
        <p className="text-gray-600">Answer a few questions to see which regulations apply to your AI usage and where your governance gaps are.</p>
        <form onSubmit={handleOnboarding} className="bg-white rounded-lg shadow p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
            <select value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} className="w-full border rounded-md px-3 py-2 text-sm" required>
              <option value="">Select...</option>
              {['financial_services', 'healthcare', 'ecommerce', 'saas', 'legal', 'insurance', 'other'].map((i) => <option key={i} value={i}>{i.replace('_', ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">AI Use Cases</label>
            <div className="flex flex-wrap gap-2">
              {['customer_chatbot', 'document_generation', 'email_automation', 'data_analysis', 'hr_recruitment'].map((uc) => (
                <label key={uc} className="flex items-center gap-1 text-sm">
                  <input type="checkbox" checked={form.ai_use_cases.includes(uc)} onChange={() => toggle('ai_use_cases', uc)} />
                  {uc.replace('_', ' ')}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Audience</label>
            <div className="flex gap-4">
              {['customers', 'employees', 'partners'].map((a) => (
                <label key={a} className="flex items-center gap-1 text-sm">
                  <input type="checkbox" checked={form.audience_types.includes(a)} onChange={() => toggle('audience_types', a)} />
                  {a}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Jurisdictions</label>
            <div className="flex flex-wrap gap-2">
              {['california', 'colorado', 'utah', 'new_york', 'illinois', 'eu', 'uk'].map((j) => (
                <label key={j} className="flex items-center gap-1 text-sm">
                  <input type="checkbox" checked={form.jurisdictions.includes(j)} onChange={() => toggle('jurisdictions', j)} />
                  {j.replace('_', ' ')}
                </label>
              ))}
            </div>
          </div>
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium">
            Run Assessment
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-gray-900">Governance Assessment</h2>

      {assessment && (
        <>
          {/* Score + Maturity */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className={`bg-white rounded-lg shadow p-6 border-l-4 ${assessment.coverage_score >= 80 ? 'border-green-500' : assessment.coverage_score >= 50 ? 'border-yellow-500' : 'border-red-500'}`}>
              <p className="text-sm text-gray-500">Coverage Score</p>
              <p className="text-3xl font-semibold">{assessment.coverage_score}%</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-500">Maturity Level</p>
              <span className={`mt-1 inline-block px-3 py-1 rounded-full text-sm font-medium ${MATURITY_STYLES[assessment.maturity_level]}`}>
                {assessment.maturity_level}
              </span>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-500">Missing Controls</p>
              <p className="text-3xl font-semibold text-red-600">{assessment.missing_controls.length}</p>
            </div>
          </div>

          {/* Applicable Regulations */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Applicable Regulations ({assessment.applicable_regulations.length})</h3>
            <div className="space-y-2">
              {assessment.applicable_regulations.map((r, i) => (
                <div key={i} className="flex items-start gap-3 text-sm">
                  <span className="text-blue-500 mt-0.5">&#x25CF;</span>
                  <div><strong>{r.regulation}</strong> ({r.jurisdiction}) &mdash; {r.why}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Required Controls */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Required Controls</h3>
            <table className="min-w-full text-sm">
              <thead><tr><th className="text-left py-2">Control</th><th className="text-left py-2">Required By</th><th className="text-left py-2">Status</th></tr></thead>
              <tbody>
                {assessment.required_controls.map((c, i) => (
                  <tr key={i} className="border-t">
                    <td className="py-2">{c.control}</td>
                    <td className="py-2 text-gray-500">{c.required_by.join(', ')}</td>
                    <td className="py-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${c.status === 'covered' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {c.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Examiner Questions */}
          {assessment.examiner_questions.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Examiner Questions</h3>
              <p className="text-sm text-gray-500 mb-3">Questions a regulator or auditor would ask about your missing controls:</p>
              <ul className="space-y-2">
                {assessment.examiner_questions.map((q, i) => (
                  <li key={i} className="text-sm flex items-start gap-2">
                    <span className="text-red-500">?</span> {q}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {assessment.recommendations.length > 0 && (
            <div className="bg-blue-50 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">Recommendations</h3>
              <ul className="space-y-2">
                {assessment.recommendations.map((r, i) => (
                  <li key={i} className="text-sm text-blue-800 flex items-start gap-2">
                    <span>&#x2192;</span> {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* Gaps */}
      {gaps && gaps.gap_count > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Described vs. Established Gaps ({gaps.gap_count})</h3>
          <div className="space-y-3">
            {gaps.gaps.map((g, i) => (
              <div key={i} className="border rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${g.risk === 'high' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}`}>{g.risk}</span>
                  <span className="text-xs text-gray-400">{g.gap_type}</span>
                </div>
                <p className="text-sm">{g.description}</p>
                <p className="text-sm text-blue-600 mt-1">Fix: {g.fix}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Four Questions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Four Questions Framework</h3>
        <form onSubmit={handleFourQuestions} className="space-y-3">
          {[
            ['purpose', 'What is this AI system for?'],
            ['working', 'How do you know it is working correctly?'],
            ['failure', 'What happens when it fails?'],
            ['accountability', 'Who is responsible?'],
          ].map(([key, label]) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <textarea value={fourQ[key]} onChange={(e) => setFourQ({ ...fourQ, [key]: e.target.value })} rows={2}
                className="w-full border rounded-md px-3 py-2 text-sm" placeholder="Your answer..." />
            </div>
          ))}
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium">
            Submit
          </button>
        </form>
        {fourQResult && (
          <div className="mt-4 border-t pt-4 space-y-3">
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${MATURITY_STYLES[fourQResult.maturity_level]}`}>
                {fourQResult.maturity_level}
              </span>
              <span className="text-sm text-gray-500">Score: {fourQResult.maturity_score}/4</span>
            </div>
            <p className="text-sm text-gray-600">{fourQResult.maturity_breakdown}</p>
            {Object.entries(fourQResult.questions).map(([key, q]) => (
              <div key={key} className="text-sm border-l-2 pl-3 border-gray-200">
                <p className="font-medium capitalize">{key}</p>
                {q.assessment && <p className="text-gray-600">{q.assessment}</p>}
                {q.gap && <p className="text-red-600">{q.gap}</p>}
                {q.recommendation && <p className="text-blue-600">{q.recommendation}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
