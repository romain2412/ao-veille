import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Navbar({ totalCount, newCount }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="bg-brand-500 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center shrink-0">
            <span className="text-brand-500 font-bold text-base">FB</span>
          </div>
          <div>
            <div className="text-brand-100 text-xs font-medium tracking-widest uppercase">
              VRD ET PAYSAGE — Veille AO
            </div>
          </div>
        </div>

        {/* Stats + user */}
        <div className="flex items-center gap-6">
          {totalCount > 0 && (
            <div className="text-right hidden sm:block">
              <div className="text-white font-semibold text-sm">{totalCount} appels d'offres</div>
              {newCount > 0 && (
                <div className="text-brand-200 text-xs font-medium">
                  {newCount} nouveau{newCount > 1 ? 'x' : ''}
                </div>
              )}
            </div>
          )}
          <div className="flex items-center gap-3">
            <span className="text-brand-100 text-sm font-medium hidden sm:block">
              {user?.full_name || user?.email}
            </span>
            <button
              onClick={handleLogout}
              className="text-sm border border-white/40 hover:border-white hover:bg-white hover:text-brand-500 text-white px-4 py-1.5 rounded-pill transition-all duration-200 font-semibold tracking-wide"
            >
              DÉCONNEXION
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}
