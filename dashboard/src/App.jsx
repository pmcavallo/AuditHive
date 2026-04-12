import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import Overview from './pages/Overview';
import AuditTrail from './pages/AuditTrail';
import Policies from './pages/Policies';
import Templates from './pages/Templates';
import Assessment from './pages/Assessment';
import RegulatoryTimeline from './pages/RegulatoryTimeline';
import Reports from './pages/Reports';
import Alerts from './pages/Alerts';
import Settings from './pages/Settings';

function PrivateRoute({ children }) {
  const apiKey = localStorage.getItem('audithive_api_key');
  return apiKey ? children : <Navigate to="/login" />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <PrivateRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/assessment" element={<Assessment />} />
                <Route path="/regulatory" element={<RegulatoryTimeline />} />
                <Route path="/audit" element={<AuditTrail />} />
                <Route path="/policies" element={<Policies />} />
                <Route path="/templates" element={<Templates />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/alerts" element={<Alerts />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Layout>
          </PrivateRoute>
        }
      />
    </Routes>
  );
}
