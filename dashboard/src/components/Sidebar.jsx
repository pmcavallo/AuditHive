import { NavLink, useNavigate } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: '\u2302' },
  { to: '/assessment', label: 'Assessment', icon: '\u2611' },
  { to: '/regulatory', label: 'Reg Timeline', icon: '\u23F0' },
  { to: '/audit', label: 'Audit Trail', icon: '\u2630' },
  { to: '/policies', label: 'Policies', icon: '\u26E8' },
  { to: '/templates', label: 'Templates', icon: '\u2B1A' },
  { to: '/reports', label: 'Reports', icon: '\u2193' },
  { to: '/alerts', label: 'Alerts', icon: '\u26A0' },
  { to: '/settings', label: 'Settings', icon: '\u2699' },
];

export default function Sidebar() {
  const navigate = useNavigate();

  function handleLogout() {
    localStorage.removeItem('audithive_api_key');
    navigate('/login');
  }

  return (
    <aside className="fixed top-0 left-0 h-screen w-60 bg-gray-900 text-white flex flex-col">
      <div className="px-6 py-5 border-b border-gray-800">
        <h1 className="text-xl font-bold tracking-tight">AuditHive</h1>
        <p className="text-xs text-gray-400 mt-0.5">AI Governance Dashboard</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            <span className="text-lg">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 pb-4">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:bg-gray-800 hover:text-white"
        >
          <span className="text-lg">{'\u2190'}</span>
          Logout
        </button>
      </div>
    </aside>
  );
}
