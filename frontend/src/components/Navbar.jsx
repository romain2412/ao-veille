import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Navbar({ newCount }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="bg-brand-500 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center">
            <span className="text-brand-500 font-bold text-sm">FB</span>
          </div>
          <div>
            <span className="font-bold text-lg">Veille AO</span>
            <span className="text-brand-100 text-sm ml-2">FB VRD</span>
          </div>
          {newCount > 0 && (
            <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
              {newCount} nouveau{newCount > 1 ? 'x' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className="text-brand-100 text-sm">{user?.full_name || user?.email}</span>
          <button
            onClick={handleLogout}
            className="text-sm bg-brand-700 hover:bg-brand-600 px-3 py-1.5 rounded-lg transition"
          >
            Déconnexion
          </button>
        </div>
      </div>
    </nav>
  )
}
