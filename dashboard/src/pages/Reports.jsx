import { useEffect, useState } from 'react';
import { api } from '../api';

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [periodDays, setPeriodDays] = useState(30);
  const [includeExaminer, setIncludeExaminer] = useState(true);

  function loadReports() {
    api.getReports().then(async (r) => {
      if (r && r.ok) setReports((await r.json()).reports);
      setLoading(false);
    });
  }

  useEffect(() => { loadReports(); }, []);

  async function handleGenerate() {
    setGenerating(true);
    const r = await api.generateReport({ period_days: periodDays, include_examiner_simulation: includeExaminer });
    if (r && r.ok) loadReports();
    setGenerating(false);
  }

  async function handleDownload(id) {
    const r = await api.downloadReport(id);
    if (r && r.ok) {
      const html = await r.text();
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Reports</h2>

      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-800">Generate Report</h3>
        <div className="flex items-center gap-4">
          <label className="text-sm">
            Period:
            <select value={periodDays} onChange={(e) => setPeriodDays(Number(e.target.value))}
              className="ml-2 border rounded px-2 py-1 text-sm">
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
          </label>
          <label className="text-sm flex items-center gap-1">
            <input type="checkbox" checked={includeExaminer} onChange={(e) => setIncludeExaminer(e.target.checked)} />
            Include examiner simulation
          </label>
          <button onClick={handleGenerate} disabled={generating}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm font-medium">
            {generating ? 'Generating...' : 'Generate Report'}
          </button>
        </div>
      </div>

      {loading ? <p className="text-gray-500">Loading...</p> : reports.length === 0 ? (
        <p className="text-gray-500 text-center py-10">No reports generated yet.</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Coverage</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Maturity</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {reports.map((r) => (
                <tr key={r.id}>
                  <td className="px-6 py-4 text-sm">{new Date(r.created_at).toLocaleDateString()}</td>
                  <td className="px-6 py-4 text-sm">{r.report_type}</td>
                  <td className="px-6 py-4 text-sm">{r.coverage_score != null ? `${r.coverage_score}%` : '-'}</td>
                  <td className="px-6 py-4 text-sm">{r.maturity_level || '-'}</td>
                  <td className="px-6 py-4">
                    <button onClick={() => handleDownload(r.id)} className="text-sm text-blue-600 hover:underline">
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
