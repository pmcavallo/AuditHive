import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

export default function Settings() {
  const apiKey = localStorage.getItem('audithive_api_key') || '';
  const prefix = apiKey.startsWith('ah-') ? apiKey.slice(0, 11) + '...' : '(unknown)';
  const [exporting, setExporting] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();

  async function handleExport() {
    setExporting(true);
    const r = await api.exportAccount();
    if (r && r.ok) {
      const data = await r.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'audithive-export.json';
      a.click();
    }
    setExporting(false);
  }

  async function handleDelete() {
    setDeleting(true);
    const r = await api.deleteAccount();
    if (r && r.ok) {
      localStorage.removeItem('audithive_api_key');
      navigate('/login');
    }
    setDeleting(false);
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-900">Settings</h2>

      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-800">Account</h3>
        <div className="text-sm">
          <p className="text-gray-500">Connected API Key</p>
          <p className="font-mono text-gray-700">{prefix}</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-800">Data Management</h3>
        <div className="flex gap-3">
          <button onClick={handleExport} disabled={exporting}
            className="px-4 py-2 text-sm font-medium border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50">
            {exporting ? 'Exporting...' : 'Export All Data'}
          </button>
        </div>
        <p className="text-xs text-gray-400">Downloads a JSON file with all your customer data including audit logs, policies, assessments, and reports.</p>
      </div>

      <div className="bg-white rounded-lg shadow p-6 border border-red-200 space-y-4">
        <h3 className="text-lg font-semibold text-red-800">Danger Zone</h3>
        {!showDelete ? (
          <button onClick={() => setShowDelete(true)}
            className="px-4 py-2 text-sm font-medium border border-red-300 text-red-600 rounded-md hover:bg-red-50">
            Delete All Data
          </button>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-red-700">This permanently deletes ALL your data. This action cannot be undone.</p>
            <div className="flex gap-2">
              <button onClick={handleDelete} disabled={deleting}
                className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50">
                {deleting ? 'Deleting...' : 'Confirm Delete'}
              </button>
              <button onClick={() => setShowDelete(false)}
                className="px-4 py-2 text-sm font-medium border rounded-md hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
