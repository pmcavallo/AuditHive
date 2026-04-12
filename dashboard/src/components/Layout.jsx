import Sidebar from './Sidebar';
import { IS_DEMO } from '../api';

export default function Layout({ children }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-60 flex-1 bg-gray-50">
        {IS_DEMO && (
          <div className="bg-amber-50 border-b border-amber-200 px-8 py-2 text-center">
            <p className="text-sm text-amber-800">
              Demo Mode — Viewing example data for a simulated e-commerce company
            </p>
          </div>
        )}
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
