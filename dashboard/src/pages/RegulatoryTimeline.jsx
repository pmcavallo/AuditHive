import { useEffect, useState } from 'react';
import { api } from '../api';

const IMPACT_STYLES = {
  critical: { border: 'border-red-500', bg: 'bg-red-100', text: 'text-red-800' },
  high: { border: 'border-orange-500', bg: 'bg-orange-100', text: 'text-orange-800' },
  medium: { border: 'border-yellow-500', bg: 'bg-yellow-100', text: 'text-yellow-800' },
  low: { border: 'border-gray-400', bg: 'bg-gray-100', text: 'text-gray-800' },
};

export default function RegulatoryTimeline() {
  const [impacts, setImpacts] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getRegulatoryImpact().then(async (r) => r && r.ok && setImpacts(await r.json())),
      api.getRegulatoryTimeline(180).then(async (r) => r && r.ok && setTimeline((await r.json()).timeline)),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  if (!impacts || impacts.impacts.length === 0) {
    return (
      <div className="text-center py-20">
        <h2 className="text-xl font-semibold text-gray-700 mb-2">No regulatory impacts found</h2>
        <p className="text-gray-500">Complete your profile in the Assessment page to see which regulations affect you.</p>
      </div>
    );
  }

  const { summary } = impacts;

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-gray-900">Regulatory Timeline</h2>

      {/* Top metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Upcoming Deadlines (90 days)</p>
          <p className="text-3xl font-semibold">{timeline.filter((t) => t.days_away <= 90).length}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Actions Required</p>
          <p className="text-3xl font-semibold text-orange-600">{summary.actions_required}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Next Deadline</p>
          <p className="text-lg font-semibold">{summary.next_deadline || 'None'}</p>
          <p className="text-xs text-gray-400">{summary.next_deadline_regulation}</p>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-4">
        {impacts.impacts.map((item) => {
          const style = IMPACT_STYLES[item.impact_level] || IMPACT_STYLES.low;
          return (
            <div key={item.id} className={`bg-white rounded-lg shadow border-l-4 ${style.border} p-6`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
                      {item.impact_level}
                    </span>
                    <span className="text-xs text-gray-400">{item.regulatory_update.jurisdiction}</span>
                    {item.days_until_deadline != null && (
                      <span className="text-xs text-gray-500">{item.days_until_deadline} days away</span>
                    )}
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900">{item.regulatory_update.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{item.regulatory_update.summary}</p>

                  {item.reasons.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs font-medium text-gray-500 uppercase">Why this affects you</p>
                      <ul className="mt-1 text-sm text-gray-600 space-y-0.5">
                        {item.reasons.map((r, i) => <li key={i}>- {r}</li>)}
                      </ul>
                    </div>
                  )}

                  {item.controls_missing.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs font-medium text-red-600 uppercase">Missing Controls</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {item.controls_missing.map((c, i) => (
                          <span key={i} className="px-2 py-0.5 bg-red-50 text-red-700 rounded text-xs">{c.control}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {item.required_actions.length > 0 && (
                    <details className="mt-3">
                      <summary className="text-sm text-blue-600 cursor-pointer hover:underline">
                        Required actions ({item.required_actions.length})
                      </summary>
                      <ul className="mt-1 text-sm text-gray-600 space-y-1 pl-4">
                        {item.required_actions.map((a, i) => (
                          <li key={i}>
                            {a.action}
                            {a.deadline && <span className="text-xs text-gray-400 ml-1">(by {a.deadline})</span>}
                            {a.effort === 'one_click' && <span className="ml-1 text-xs text-green-600">[one-click fix]</span>}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>

                {!item.acknowledged && (
                  <button
                    onClick={async () => {
                      await api.acknowledgeImpact(item.id);
                      const r = await api.getRegulatoryImpact();
                      if (r && r.ok) setImpacts(await r.json());
                    }}
                    className="px-3 py-1 text-xs border rounded hover:bg-gray-50 shrink-0"
                  >
                    Acknowledge
                  </button>
                )}
                {item.acknowledged && (
                  <span className="text-xs text-green-600 shrink-0">Acknowledged</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
