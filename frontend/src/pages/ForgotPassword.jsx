import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { forgotPassword } from '../api/client'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await forgotPassword(email)
      // La réponse est volontairement générique (anti-énumération d'emails).
      setMessage(res?.message || "Si un compte est associé à cette adresse, un email vient d'être envoyé.")
      setDone(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Une erreur est survenue. Réessayez plus tard.')
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
          <h1 className="text-2xl font-semibold text-brand-500">Mot de passe oublié</h1>
          <p className="text-fbslate text-sm mt-1 font-medium tracking-wide uppercase">
            Veille Appels d'Offres
          </p>
        </div>

        {done ? (
          <div className="text-center space-y-6">
            <p className="text-green-700 text-sm bg-green-50 border border-green-200 rounded-lg px-4 py-3">
              {message}
            </p>
            <button
              onClick={() => navigate('/login')}
              className="text-sm text-brand-500 font-semibold hover:underline"
            >
              Retour à la connexion
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm text-fbslate mb-6 text-center">
              Saisissez l'adresse email de votre compte. Si elle est enregistrée,
              vous recevrez un lien pour redéfinir votre mot de passe.
            </p>

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
                {loading ? 'Envoi…' : 'ENVOYER LE LIEN'}
              </button>

              <div className="text-center">
                <Link
                  to="/login"
                  className="text-sm text-brand-500 hover:underline font-medium"
                >
                  Retour à la connexion
                </Link>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
