import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Tenders from './pages/Tenders'
import Admin from './pages/Admin'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 60_000 } },
})

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Chargement…</div>
  return user ? children : <Navigate to="/login" replace />
}

// Accès réservé aux administrateurs (sinon redirection vers l'accueil).
// NB : protection de confort côté front — la vraie sécurité est côté API
// (routes /admin protégées par get_admin_user → 403 si non-admin).
function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Chargement…</div>
  if (!user) return <Navigate to="/login" replace />
  return user.is_admin ? children : <Navigate to="/" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<PrivateRoute><Tenders /></PrivateRoute>} />
            <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
