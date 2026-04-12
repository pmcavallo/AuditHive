import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, IS_DEMO } from '../api';

export default function Login() {
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (IS_DEMO) {
      localStorage.setItem('audithive_api_key', 'demo');
      navigate('/');
    }
  }, [navigate]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const resp = await api.checkHealth(apiKey);
      if (resp.ok) {
        localStorage.setItem('audithive_api_key', apiKey);
        navigate('/');
      } else {
        setError('Invalid API key. Please check and try again.');
      }
    } catch {
      setError('Could not connect to the AuditHive API.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-gray-900">AuditHive</h1>
            <p className="text-sm text-gray-500 mt-1">AI Governance Dashboard</p>
          </div>

          {IS_DEMO && (
            <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
              <p className="text-sm text-blue-800 font-medium">Live demo with example data. No backend required.</p>
              <p className="text-xs text-blue-600">Redirecting...</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 mb-1">
                API Key
              </label>
              <input
                id="apiKey"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="ah-..."
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <button
              type="submit"
              disabled={loading || !apiKey}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Connecting...' : 'Connect'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
