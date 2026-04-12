const STATUS_STYLES = {
  completed: 'bg-green-100 text-green-800',
  blocked: 'bg-red-100 text-red-800',
  flagged: 'bg-yellow-100 text-yellow-800',
  error: 'bg-gray-100 text-gray-800',
};

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.error;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style}`}>
      {status}
    </span>
  );
}
