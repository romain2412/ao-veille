import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('Email ou mot de passe incorrect')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-fbgray flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-brand-500 rounded-full mb-4">
            <span className="text-white font-bold text-3xl" style={{ fontFamily: 'Poppins' }}>FB</span>
          </div>
          <h1 className="text-2xl font-semibold text-brand-500">Veille Appels d'Offres</h1>
          <p className="text-fbslate text-sm mt-1 font-medium tracking-wide uppercase">
            Bureau d'études VRD &amp; Paysage
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-fbtext mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent font-medium"
              placeholder="vous@fb-vrd.fr"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-fbtext mb-1">Mot de passe</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent font-medium"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white font-semibold py-3 rounded-pill transition-all duration-200 disabled:opacity-50 tracking-wide"
          >
            {loading ? 'Connexion…' : 'SE CONNECTER'}
          </button>

          <div className="text-center">
            <Link
              to="/forgot-password"
              className="text-sm text-brand-500 hover:underline font-medium"
            >
              Mot de passe oublié ?
            </Link>
          </div>
        </form>

        <p className="text-center text-xs text-fbslate mt-6">
          Bureau d'études VRD &amp; Paysage
        </p>
      </div>
    </div>
  )
}
