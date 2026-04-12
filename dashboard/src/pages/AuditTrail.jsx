import { useEffect, useState } from 'react';
import { api } from '../api';
import StatusBadge from '../components/StatusBadge';
import Pagination from '../components/Pagination';

const PAGE_SIZE = 20;

export default function AuditTrail() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = { limit: PAGE_SIZE, offset };
    if (statusFilter) params.status = statusFilter;
    api.getAuditLogs(params).then(async (r) => {
      if (r) {
        const data = await r.json();
        setLogs(data.logs);
        setTotal(data.total);
      }
      setLoading(false);
    });
  }, [offset, statusFilter]);

  function handleStatusChange(e) {
    setStatusFilter(e.target.value);
    setOffset(0);
  }

  function userMessage(messages) {
    if (!messages) return '';
    const msg = messages.find((m) => m.role === 'user');
    const text = msg?.content || '';
    return text.length > 80 ? text.slice(0, 80) + '...' : text;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Audit Trail</h2>
        <select
          value={statusFilter}
          onChange={handleStatusChange}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="blocked">Blocked</option>
          <option value="flagged">Flagged</option>
          <option value="error">Error</option>
        </select>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : logs.length === 0 ? (
        <p className="text-gray-500 text-center py-10">No audit logs found.</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">User Message</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Violations</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Latency</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {logs.map((log) => (
                <tr
                  key={log.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setSelectedLog(selectedLog?.id === log.id ? null : log)}
                >
                  <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <StatusBadge status={log.status} />
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">{log.request_model}</td>
                  <td className="px-6 py-4 text-sm text-gray-700 max-w-xs truncate">
                    {userMessage(log.request_messages)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {log.policies_violated?.length || 'None'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {log.response_latency_ms != null ? `${log.response_latency_ms}ms` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <Pagination offset={offset} limit={PAGE_SIZE} total={total} onChange={setOffset} />
        </div>
      )}

      {/* Detail panel */}
      {selectedLog && (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-800">Log Detail</h3>
            <button onClick={() => setSelectedLog(null)} className="text-sm text-gray-500 hover:text-gray-700">
              Close
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium text-gray-500">ID</p>
              <p className="font-mono text-xs">{selectedLog.id}</p>
            </div>
            <div>
              <p className="font-medium text-gray-500">Status</p>
              <StatusBadge status={selectedLog.status} />
            </div>
            <div>
              <p className="font-medium text-gray-500">Tokens In</p>
              <p>{selectedLog.response_tokens_in ?? '-'}</p>
            </div>
            <div>
              <p className="font-medium text-gray-500">Tokens Out</p>
              <p>{selectedLog.response_tokens_out ?? '-'}</p>
            </div>
          </div>
          <div>
            <p className="font-medium text-gray-500 text-sm mb-1">Request Messages</p>
            <pre className="bg-gray-50 rounded p-3 text-xs overflow-auto max-h-48">
              {JSON.stringify(selectedLog.request_messages, null, 2)}
            </pre>
          </div>
          <div>
            <p className="font-medium text-gray-500 text-sm mb-1">Response</p>
            <pre className="bg-gray-50 rounded p-3 text-xs overflow-auto max-h-48">
              {JSON.stringify(selectedLog.response_content, null, 2)}
            </pre>
          </div>
          {selectedLog.policies_applied?.length > 0 && (
            <div>
              <p className="font-medium text-gray-500 text-sm mb-1">Policies Applied</p>
              <pre className="bg-gray-50 rounded p-3 text-xs overflow-auto max-h-48">
                {JSON.stringify(selectedLog.policies_applied, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
