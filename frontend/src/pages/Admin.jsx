import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getMonitoring } from '../api/client'

const SOURCE_LABELS = {
  boamp: 'BOAMP',
  demat_ampa: 'AMPA',
  e_marches_publics: 'e-MP',
  noalis: 'Noalis',
  vilogia: 'Vilogia',
  aquitanis: 'Aquitanis',
}

// Code couleur des sources (identique au bandeau de la page application)
const SOURCE_COLORS = {
  boamp: 'bg-blue-100 text-blue-700 border-blue-200',
  demat_ampa: 'bg-purple-100 text-purple-700 border-purple-200',
  e_marches_publics: 'bg-orange-100 text-orange-700 border-orange-200',
  noalis: 'bg-green-100 text-green-700 border-green-200',
  vilogia: 'bg-red-100 text-red-700 border-red-200',
  aquitanis: 'bg-teal-100 text-teal-700 border-teal-200',
}

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
          </div>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="text-sm border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white font-semibold px-4 py-2 rounded-pill transition-all duration-200 disabled:opacity-50"
          >
            {isFetching ? 'Actualisation…' : '↻ Actualiser'}
          </button>
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
                  <th className="text-right font-bold px-4 py-3" title="AO ayant passé le score et insérés en base">Récupéré</th>
                  <th className="text-right font-bold px-4 py-3" title="Durée du dernier run">Durée</th>
                  <th className="text-left font-bold px-4 py-3">Date</th>
                </tr>
              </thead>
              <tbody>
                {data.sources.map(s => (
                  <tr key={s.source} className="border-t border-gray-100 hover:bg-fbgray/50">
                    <td className="px-4 py-3">
                      <span className={`text-xs font-bold px-3 py-1 rounded-pill border ${SOURCE_COLORS[s.source] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>
                        {SOURCE_LABELS[s.source] || s.source}
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
                      {s.last_run ? s.last_run.inserted_count : '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-fbslate whitespace-nowrap">
                      {s.last_run ? formatDuration(s.last_run.duration_seconds) : '—'}
                    </td>
                    <td className="px-4 py-3 text-fbslate whitespace-nowrap">
                      {formatDateTime(s.last_run?.finished_at || s.last_run?.started_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
