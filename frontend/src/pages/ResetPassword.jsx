import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getResetInfo, resetPassword } from '../api/client'

export default function ResetPassword() {
  const { token } = useParams()
  const navigate = useNavigate()

  const [info, setInfo] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    getResetInfo(token)
      .then(setInfo)
      .catch(err => {
        setLoadError(err.response?.data?.detail || "Ce lien de réinitialisation n'est pas valide.")
      })
  }, [token])

  const handleSubmit = async e => {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caractères.')
      return
    }
    if (password !== confirm) {
      setError('Les deux mots de passe ne correspondent pas.')
      return
    }
    setSubmitting(true)
    try {
      await resetPassword(token, password)
      setDone(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Une erreur est survenue.')
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-fbgray flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-brand-500 rounded-full mb-4">
            <span className="text-white font-bold text-3xl" style={{ fontFamily: 'Poppins' }}>FB</span>
          </div>
          <h1 className="text-2xl font-semibold text-brand-500">Nouveau mot de passe</h1>
          <p className="text-fbslate text-sm mt-1 font-medium tracking-wide uppercase">
            Veille Appels d'Offres
          </p>
        </div>

        {loadError && (
          <div className="text-center">
            <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-3">
              {loadError}
            </p>
            <button onClick={() => navigate('/forgot-password')} className="mt-4 text-sm text-brand-500 font-semibold">
              Demander un nouveau lien
            </button>
          </div>
        )}

        {done && (
          <p className="text-green-700 text-sm bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-center">
            ✓ Mot de passe modifié. Redirection vers la connexion…
          </p>
        )}

        {!loadError && !done && info && (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-fbtext mb-1">Email</label>
              <input
                type="email"
                value={info.email}
                disabled
                className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm bg-fbgray text-fbslate font-medium"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-fbtext mb-1">Nouveau mot de passe</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                placeholder="Au moins 8 caractères"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent font-medium"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-fbtext mb-1">Confirmer le mot de passe</label>
              <input
                type="password"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent font-medium"
              />
            </div>

            {error && (
              <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white font-semibold py-3 rounded-pill transition-all duration-200 disabled:opacity-50 tracking-wide"
            >
              {submitting ? 'Enregistrement…' : 'CHANGER MON MOT DE PASSE'}
            </button>
          </form>
        )}

        {!loadError && !done && !info && (
          <p className="text-center text-fbslate text-sm">Chargement…</p>
        )}
      </div>
    </div>
  )
}
