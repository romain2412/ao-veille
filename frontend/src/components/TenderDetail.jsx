import { markSeen } from '../api/client'
import { useQueryClient } from '@tanstack/react-query'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', {
    weekday: 'long', day: '2-digit', month: 'long', year: 'numeric'
  })
}

function daysLeft(iso) {
  if (!iso) return null
  return Math.ceil((new Date(iso) - new Date()) / 86400000)
}

export default function TenderDetail({ tender, onClose }) {
  const queryClient = useQueryClient()
  const days = daysLeft(tender.deadline)

  const handleMarkSeen = async () => {
    await markSeen(tender.id)
    queryClient.invalidateQueries({ queryKey: ['tenders'] })
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* En-tête */}
        <div className="sticky top-0 bg-white border-b border-gray-100 px-6 py-4 flex items-start justify-between rounded-t-2xl">
          <div className="flex items-center gap-2 flex-wrap">
            {tender.is_new && (
              <span className="bg-brand-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">NOUVEAU</span>
            )}
            {tender.is_priority_region && (
              <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-2 py-0.5 rounded-full">📍 Nouvelle-Aquitaine</span>
            )}
            <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">{tender.market_type}</span>
            <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">{tender.notice_nature}</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-4">✕</button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Titre + score */}
          <div className="flex items-start justify-between gap-4">
            <h2 className="text-lg font-bold text-gray-800 leading-snug">{tender.title}</h2>
            <span className="shrink-0 text-sm font-bold bg-green-100 text-green-800 px-3 py-1 rounded-full">
              {tender.score} pts
            </span>
          </div>

          {/* Description */}
          {tender.description && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Description</h3>
              <p className="text-sm text-gray-700 leading-relaxed">{tender.description}</p>
            </div>
          )}

          {/* Infos clés */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-xl p-3">
              <p className="text-xs text-gray-500 mb-0.5">Acheteur</p>
              <p className="text-sm font-medium text-gray-800">{tender.buyer_name || '—'}</p>
              {tender.buyer_city && <p className="text-xs text-gray-500">{tender.buyer_city}</p>}
            </div>
            <div className="bg-gray-50 rounded-xl p-3">
              <p className="text-xs text-gray-500 mb-0.5">Lieu d'exécution</p>
              <p className="text-sm font-medium text-gray-800">{tender.execution_location || '—'}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-3">
              <p className="text-xs text-gray-500 mb-0.5">Publication</p>
              <p className="text-sm font-medium text-gray-800">{formatDate(tender.publication_date)}</p>
            </div>
            <div className={`rounded-xl p-3 ${days !== null && days <= 7 ? 'bg-red-50' : 'bg-gray-50'}`}>
              <p className="text-xs text-gray-500 mb-0.5">Date limite de réponse</p>
              <p className={`text-sm font-medium ${days !== null && days <= 7 ? 'text-red-700' : 'text-gray-800'}`}>
                {formatDate(tender.deadline)}
              </p>
              {days !== null && (
                <p className={`text-xs mt-0.5 ${days <= 7 ? 'text-red-600 font-semibold' : 'text-gray-500'}`}>
                  {days > 0 ? `${days} jours restants` : 'Expiré'}
                </p>
              )}
            </div>
          </div>

          {/* Départements */}
          {tender.departments?.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Départements</h3>
              <div className="flex flex-wrap gap-2">
                {tender.departments.map(d => (
                  <span key={d} className="text-sm bg-gray-100 px-3 py-1 rounded-full">{d}</span>
                ))}
              </div>
            </div>
          )}

          {/* Mots-clés déclencheurs */}
          {tender.matched_keywords?.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Mots-clés détectés</h3>
              <div className="flex flex-wrap gap-2">
                {tender.matched_keywords.map(kw => (
                  <span key={kw} className="text-sm bg-brand-50 text-brand-700 border border-brand-100 px-3 py-1 rounded-full">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2 border-t border-gray-100">
            {tender.url && (
              <a
                href={tender.url}
                target="_blank"
                rel="noreferrer"
                className="flex-1 text-center bg-brand-500 hover:bg-brand-600 text-white font-semibold py-2.5 rounded-xl transition"
              >
                Voir l'avis complet →
              </a>
            )}
            {tender.is_new && (
              <button
                onClick={handleMarkSeen}
                className="flex-1 text-center border border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold py-2.5 rounded-xl transition"
              >
                Marquer comme vu
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
