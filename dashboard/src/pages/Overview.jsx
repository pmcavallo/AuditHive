import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { api } from '../api';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';

const MATURITY_STYLES = {
  mature: 'bg-green-100 text-green-800',
  developing: 'bg-yellow-100 text-yellow-800',
  immature: 'bg-orange-100 text-orange-800',
  ungoverned: 'bg-red-100 text-red-800',
};

export default function Overview() {
  const [stats, setStats] = useState(null);
  const [assessment, setAssessment] = useState(null);
  const [hasProfile, setHasProfile] = useState(true);
  const [regImpact, setRegImpact] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      api.getAuditStats(7).then(async (r) => r && setStats(await r.json())),
      api.getAssessment().then(async (r) => {
        if (r && r.ok) setAssessment(await r.json());
        else setHasProfile(false);
      }),
      api.getRegulatoryImpact({ days_ahead: 90 }).then(async (r) => {
        if (r && r.ok) setRegImpact(await r.json());
      }),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  if (!stats || stats.total_calls === 0) {
    return (
      <div className="text-center py-20">
        <h2 className="text-xl font-semibold text-gray-700 mb-2">No data yet</h2>
        <p className="text-gray-500">
          Send your first request through AuditHive to see governance metrics here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-gray-900">Overview</h2>

      {/* Metric cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="Total Calls" value={stats.total_calls} color="blue" />
        <MetricCard title="Policy Violations" value={stats.total_blocked + stats.total_flagged} color="yellow" />
        <MetricCard title="Blocked" value={stats.total_blocked} color="red" />
        <MetricCard title="Active Policies" value={stats.active_policies} color="green" />
      </div>

      {/* Governance metrics */}
      {!hasProfile && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
          <div>
            <p className="font-medium text-blue-900">Answer 4 questions to see your governance coverage</p>
            <p className="text-sm text-blue-700">Find out which regulations apply and where your gaps are.</p>
          </div>
          <button onClick={() => navigate('/assessment')} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium">
            Start Assessment
          </button>
        </div>
      )}
      {assessment && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className={`bg-white rounded-lg shadow p-6 border-l-4 ${assessment.coverage_score >= 80 ? 'border-green-500' : assessment.coverage_score >= 50 ? 'border-yellow-500' : 'border-red-500'}`}>
            <p className="text-sm text-gray-500">Governance Coverage</p>
            <p className="text-3xl font-semibold">{assessment.coverage_score}%</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-sm text-gray-500">Maturity Level</p>
            <span className={`mt-1 inline-block px-3 py-1 rounded-full text-sm font-medium ${MATURITY_STYLES[assessment.maturity_level]}`}>
              {assessment.maturity_level}
            </span>
          </div>
          <div className="bg-white rounded-lg shadow p-6 cursor-pointer hover:bg-gray-50" onClick={() => navigate('/assessment')}>
            <p className="text-sm text-gray-500">Gaps Found</p>
            <p className="text-3xl font-semibold text-red-600">{assessment.missing_controls.length}</p>
            <p className="text-xs text-blue-600 mt-1">View full assessment &rarr;</p>
          </div>
        </div>
      )}

      {/* Regulatory alert banner */}
      {regImpact && (regImpact.summary.critical > 0 || regImpact.summary.high > 0) && (
        <div className={`rounded-lg p-4 flex items-center justify-between ${regImpact.summary.critical > 0 ? 'bg-red-50 border border-red-200' : 'bg-orange-50 border border-orange-200'}`}>
          <div>
            <p className={`font-medium ${regImpact.summary.critical > 0 ? 'text-red-900' : 'text-orange-900'}`}>
              {regImpact.summary.next_deadline_regulation} — deadline {regImpact.summary.next_deadline}
            </p>
            <p className={`text-sm ${regImpact.summary.critical > 0 ? 'text-red-700' : 'text-orange-700'}`}>
              {regImpact.summary.actions_required} action(s) required across {regImpact.summary.total_affecting} regulation(s)
            </p>
          </div>
          <button onClick={() => navigate('/regulatory')}
            className={`px-4 py-2 rounded-md text-sm font-medium ${regImpact.summary.critical > 0 ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-orange-600 text-white hover:bg-orange-700'}`}>
            View Timeline
          </button>
        </div>
      )}

      {/* Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Calls per Day (Last 7 Days)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={stats.calls_by_day}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="total" stroke="#3b82f6" name="Total" strokeWidth={2} />
            <Line type="monotone" dataKey="violations" stroke="#ef4444" name="Violations" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Recent violations */}
      {stats.recent_violations.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800">Recent Violations</h3>
          </div>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Message</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {stats.recent_violations.map((v) => (
                <tr
                  key={v.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/audit?id=${v.id}`)}
                >
                  <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
                    {new Date(v.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <StatusBadge status={v.status} />
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">{v.request_model}</td>
                  <td className="px-6 py-4 text-sm text-gray-700 max-w-xs truncate">{v.message_preview}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
