import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import {
  getMonitoring, triggerCollection, triggerCollectionAll, getCollectionStatus,
  createInvitation, getInvitations,
} from '../api/client'
import { sourceLabel, sourceColorBordered } from '../sources'

function formatDateTime(iso) {
  if (!iso) return '—'
  // Les dates de l'API sont en UTC mais sans suffixe de fuseau ("Z").
  // On force l'interprétation UTC ; l'affichage se fait ensuite dans le
  // fuseau horaire local du navigateur de l'utilisateur (comportement par défaut).
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso)
  const d = new Date(hasTz ? iso : iso + 'Z')
  return d.toLocaleString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatDuration(seconds) {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds.toFixed(1)} s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m} min ${s} s`
}

function StatusBadge({ run }) {
  if (!run) {
    return <span className="text-xs font-semibold px-2 py-0.5 rounded-pill bg-gray-100 text-gray-500">Jamais exécuté</span>
  }
  const ok = run.status === 'success'
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-pill ${ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
      {ok ? '✓ Succès' : '✗ Erreur'}
    </span>
  )
}

export default function Admin() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['monitoring'],
    queryFn: getMonitoring,
  })

  // --- Invitations ---
  const { data: invData, refetch: refetchInvites } = useQuery({
    queryKey: ['invitations'],
    queryFn: getInvitations,
  })
  const [invEmail, setInvEmail] = useState('')
  const [invName, setInvName] = useState('')
  const [invAdmin, setInvAdmin] = useState(false)
  const [invSubmitting, setInvSubmitting] = useState(false)
  const [invError, setInvError] = useState('')
  const [invLink, setInvLink] = useState('')

  const handleCreateInvite = async (e) => {
    e.preventDefault()
    setInvError('')
    setInvLink('')
    setInvSubmitting(true)
    try {
      const res = await createInvitation({
        email: invEmail.trim(),
        full_name: invName.trim() || null,
        is_admin: invAdmin,
      })
      setInvLink(res.link)
      setInvEmail(''); setInvName(''); setInvAdmin(false)
      refetchInvites()
    } catch (err) {
      setInvError(err.response?.data?.detail || "Échec de la création de l'invitation.")
    } finally {
      setInvSubmitting(false)
    }
  }

  const copyLink = (link) => {
    const full = link.startsWith('http') ? link : `${window.location.origin}${link}`
    navigator.clipboard?.writeText(full)
  }

  // Sources pour lesquelles une collecte vient d'être demandée (bouton désactivé)
  const [requested, setRequested] = useState({})
  const [allRunning, setAllRunning] = useState(false)

  // Attend la fin (done/error) d'une demande via polling du statut.
  const waitForRequest = (requestId) => new Promise(resolve => {
    const startedAt = Date.now()
    const MAX_WAIT = 15 * 60 * 1000   // garde-fou large : 15 min (sources Playwright lentes)
    const poll = async () => {
      try {
        const st = await getCollectionStatus(requestId)
        if (st.status === 'done' || st.status === 'error') {
          resolve()
          return
        }
      } catch {
        // on retentera au prochain tick
      }
      if (Date.now() - startedAt < MAX_WAIT) setTimeout(poll, 4000)
      else resolve()   // garde-fou
    }
    setTimeout(poll, 4000)
  })

  const handleRelaunch = async (source) => {
    setRequested(prev => ({ ...prev, [source]: true }))
    try {
      const { request_id } = await triggerCollection(source)
      await waitForRequest(request_id)
      refetch()
    } finally {
      setRequested(prev => ({ ...prev, [source]: false }))
    }
  }

  const handleRelaunchAll = async () => {
    setAllRunning(true)
    try {
      const { requests } = await triggerCollectionAll()
      // Attend la fin de toutes les demandes, en rafraîchissant au fur et à mesure
      await Promise.all((requests || []).map(r =>
        waitForRequest(r.request_id).then(() => refetch())
      ))
      refetch()
    } finally {
      setAllRunning(false)
    }
  }

  return (
    <div className="min-h-screen bg-fbgray">
      <nav className="bg-brand-500 text-white shadow-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center shrink-0">
              <span className="text-brand-500 font-bold text-base">FB</span>
            </div>
            <div className="text-brand-100 text-xs font-medium tracking-widest uppercase">
              Administration &amp; Monitoring
            </div>
          </div>
          <button
            onClick={() => navigate('/')}
            className="text-sm border border-white/40 hover:border-white hover:bg-white hover:text-brand-500 text-white px-4 py-1.5 rounded-pill transition-all duration-200 font-semibold tracking-wide"
          >
            ← RETOUR
          </button>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-brand-500">Monitoring des collecteurs</h1>
            <p className="text-fbslate text-sm mt-1">
              Connecté en tant que <span className="font-semibold">{user?.email}</span>
            </p>
            {data?.next_collect_run && (
              <p className="text-fbslate text-sm mt-1">
                Prochaine collecte : <span className="font-semibold text-brand-500">{formatDateTime(data.next_collect_run)}</span>
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRelaunchAll}
              disabled={allRunning}
              className="text-sm bg-brand-500 text-white hover:bg-brand-600 font-semibold px-4 py-2 rounded-pill transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Lancer une collecte de toutes les sources"
            >
              {allRunning ? 'Collecte en cours…' : '↻ Tout relancer'}
            </button>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="text-sm border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white font-semibold px-4 py-2 rounded-pill transition-all duration-200 disabled:opacity-50"
            >
              {isFetching ? 'Actualisation…' : '↻ Actualiser'}
            </button>
          </div>
        </div>

        {isLoading && (
          <div className="text-center py-20 text-fbslate font-medium">Chargement…</div>
        )}
        {isError && (
          <div className="text-center py-20 text-red-500 font-medium">Erreur de chargement</div>
        )}

        {data && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-fbgray text-fbslate text-xs uppercase tracking-wide">
                  <th className="text-left font-bold px-4 py-3">Source</th>
                  <th className="text-center font-bold px-4 py-3">Statut</th>
                  <th className="text-right font-bold px-4 py-3" title="AO récupérés depuis le site, avant scoring">Collecté</th>
                  <th className="text-right font-bold px-4 py-3" title="AO ayant passé l'algo de scoring">Score validated</th>
                  <th className="text-right font-bold px-4 py-3" title="AO insérés (nouvelle entrée) en base">Inserted</th>
                  <th className="text-right font-bold px-4 py-3" title="AO déjà présents et mis à jour">Updated</th>
                  <th className="text-right font-bold px-4 py-3" title="Durée du dernier run">Durée</th>
                  <th className="text-left font-bold px-4 py-3">Date</th>
                  <th className="text-center font-bold px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.sources.map(s => (
                  <tr key={s.source} className="border-t border-gray-100 hover:bg-fbgray/50">
                    <td className="px-4 py-3">
                      <span className={`text-xs font-bold px-3 py-1 rounded-pill border ${sourceColorBordered(s.source)}`}>
                        {sourceLabel(s.source)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex flex-col items-center gap-1">
                        <StatusBadge run={s.last_run} />
                        {s.last_run?.error && (
                          <span className="text-xs text-red-600 max-w-[220px] truncate" title={s.last_run.error}>
                            {s.last_run.error}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-fbslate">
                      {s.last_run ? s.last_run.collected_count : '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-fbslate">
                      {s.last_run ? s.last_run.score_validated_count : '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-fbslate">
                      {s.last_run ? s.last_run.inserted_count : '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-fbslate">
                      {s.last_run ? s.last_run.updated_count : '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-fbslate whitespace-nowrap">
                      {s.last_run ? formatDuration(s.last_run.duration_seconds) : '—'}
                    </td>
                    <td className="px-4 py-3 text-fbslate whitespace-nowrap">
                      {formatDateTime(s.last_run?.finished_at || s.last_run?.started_at)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleRelaunch(s.source)}
                        disabled={requested[s.source] || allRunning}
                        className="text-xs font-semibold border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white px-3 py-1 rounded-pill transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Lancer une collecte manuelle de cette source"
                      >
                        {(requested[s.source] || allRunning) ? 'En cours…' : '↻ Relancer'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* --- Gestion des utilisateurs : inviter --- */}
        <div className="mt-10">
          <h2 className="text-xl font-semibold text-brand-500 mb-4">Inviter un utilisateur</h2>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mb-6">
            <form onSubmit={handleCreateInvite} className="flex flex-wrap gap-4 items-end">
              <div className="flex-1 min-w-[220px]">
                <label className="block text-xs font-bold text-fbslate uppercase tracking-wide mb-1">Email</label>
                <input
                  type="email"
                  value={invEmail}
                  onChange={e => setInvEmail(e.target.value)}
                  required
                  placeholder="collegue@fb-vrd.fr"
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                />
              </div>
              <div className="flex-1 min-w-[180px]">
                <label className="block text-xs font-bold text-fbslate uppercase tracking-wide mb-1">Nom (optionnel)</label>
                <input
                  type="text"
                  value={invName}
                  onChange={e => setInvName(e.target.value)}
                  placeholder="Prénom Nom"
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                />
              </div>
              <label className="flex items-center gap-2 text-sm font-semibold cursor-pointer select-none text-fbtext pb-2">
                <input
                  type="checkbox"
                  checked={invAdmin}
                  onChange={e => setInvAdmin(e.target.checked)}
                  className="w-4 h-4 accent-brand-500 rounded"
                />
                Administrateur
              </label>
              <button
                type="submit"
                disabled={invSubmitting}
                className="text-sm bg-brand-500 text-white hover:bg-brand-600 font-semibold px-5 py-2.5 rounded-pill transition-all duration-200 disabled:opacity-50"
              >
                {invSubmitting ? 'Création…' : 'Créer l\'invitation'}
              </button>
            </form>

            {invError && (
              <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-2 mt-4">
                {invError}
              </p>
            )}

            {invLink && (
              <div className="mt-4 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                <p className="text-sm text-green-800 font-semibold mb-1">Invitation créée. Lien à transmettre :</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs bg-white border border-gray-200 rounded px-3 py-2 break-all">
                    {invLink.startsWith('http') ? invLink : `${window.location.origin}${invLink}`}
                  </code>
                  <button
                    onClick={() => copyLink(invLink)}
                    className="text-xs font-semibold border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white px-3 py-2 rounded-pill transition-all duration-200 shrink-0"
                  >
                    Copier
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Liste des invitations */}
          {invData?.invitations?.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-fbgray text-fbslate text-xs uppercase tracking-wide">
                    <th className="text-left font-bold px-4 py-3">Email</th>
                    <th className="text-left font-bold px-4 py-3">Nom</th>
                    <th className="text-center font-bold px-4 py-3">Rôle</th>
                    <th className="text-center font-bold px-4 py-3">Statut</th>
                    <th className="text-left font-bold px-4 py-3">Expire le</th>
                    <th className="text-center font-bold px-4 py-3">Lien</th>
                  </tr>
                </thead>
                <tbody>
                  {invData.invitations.map(inv => (
                    <tr key={inv.id} className="border-t border-gray-100 hover:bg-fbgray/50">
                      <td className="px-4 py-3 font-medium text-fbtext">{inv.email}</td>
                      <td className="px-4 py-3 text-fbslate">{inv.full_name || '—'}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-pill ${inv.is_admin ? 'bg-brand-100 text-brand-500' : 'bg-gray-100 text-gray-600'}`}>
                          {inv.is_admin ? 'Admin' : 'Utilisateur'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-pill ${
                          inv.status === 'used' ? 'bg-green-100 text-green-700'
                          : inv.status === 'expired' ? 'bg-red-100 text-red-700'
                          : 'bg-amber-100 text-amber-700'
                        }`}>
                          {inv.status === 'used' ? 'Utilisée' : inv.status === 'expired' ? 'Expirée' : 'En attente'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-fbslate whitespace-nowrap">{formatDateTime(inv.expires_at)}</td>
                      <td className="px-4 py-3 text-center">
                        {inv.status === 'pending' ? (
                          <button
                            onClick={() => copyLink(inv.link)}
                            className="text-xs font-semibold border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white px-3 py-1 rounded-pill transition-all duration-200"
                          >
                            Copier
                          </button>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
