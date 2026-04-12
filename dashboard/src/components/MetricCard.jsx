export default function MetricCard({ title, value, color = 'blue' }) {
  const borderColor = {
    blue: 'border-blue-500',
    red: 'border-red-500',
    yellow: 'border-yellow-500',
    green: 'border-green-500',
  }[color] || 'border-blue-500';

  return (
    <div className={`bg-white rounded-lg shadow p-6 border-l-4 ${borderColor}`}>
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <p className="mt-1 text-3xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}
