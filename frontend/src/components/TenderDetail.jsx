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
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-brand-500 text-white px-6 py-4 flex items-center justify-between rounded-t-2xl">
          <div className="flex items-center gap-2 flex-wrap">
            {tender.is_new && (
              <span className="bg-white text-brand-500 text-xs font-bold px-3 py-0.5 rounded-pill">NOUVEAU</span>
            )}
            {tender.is_priority_region && (
              <span className="bg-brand-100 text-brand-500 text-xs font-semibold px-2 py-0.5 rounded-pill">📍 Nouvelle-Aquitaine</span>
            )}
            <span className="text-brand-100 text-xs font-medium">{tender.market_type} · {tender.notice_nature}</span>
          </div>
          <button onClick={onClose} className="text-white/70 hover:text-white text-xl leading-none ml-4 transition-colors">✕</button>
        </div>

        <div className="px-6 py-6 space-y-6">
          {/* Titre + score */}
          <div className="flex items-start justify-between gap-4">
            <h2 className="text-lg font-semibold text-brand-500 leading-snug">{tender.title}</h2>
            <span className="shrink-0 text-sm font-bold bg-brand-100 text-brand-500 px-3 py-1 rounded-pill">
              {tender.score} pts
            </span>
          </div>

          {/* Description */}
          {tender.description && (
            <div>
              <h3 className="text-xs font-bold text-fbslate uppercase tracking-widest mb-2">Description</h3>
              <p className="text-sm text-fbtext leading-relaxed">{tender.description}</p>
            </div>
          )}

          {/* Infos clés */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-fbgray rounded-xl p-4">
              <p className="text-xs font-bold text-fbslate uppercase tracking-wide mb-1">Acheteur</p>
              <p className="text-sm font-semibold text-fbtext">{tender.buyer_name || '—'}</p>
              {tender.buyer_city && <p className="text-xs text-fbslate mt-0.5">{tender.buyer_city}</p>}
            </div>
            <div className="bg-fbgray rounded-xl p-4">
              <p className="text-xs font-bold text-fbslate uppercase tracking-wide mb-1">Lieu d'exécution</p>
              <p className="text-sm font-semibold text-fbtext">{tender.execution_location || '—'}</p>
            </div>
            <div className="bg-fbgray rounded-xl p-4">
              <p className="text-xs font-bold text-fbslate uppercase tracking-wide mb-1">Publication</p>
              <p className="text-sm font-semibold text-fbtext">{formatDate(tender.publication_date)}</p>
            </div>
            <div className={`rounded-xl p-4 ${days !== null && days <= 7 ? 'bg-red-50' : 'bg-fbgray'}`}>
              <p className="text-xs font-bold text-fbslate uppercase tracking-wide mb-1">Date limite</p>
              <p className={`text-sm font-semibold ${days !== null && days <= 7 ? 'text-red-700' : 'text-fbtext'}`}>
                {formatDate(tender.deadline)}
              </p>
              {days !== null && (
                <p className={`text-xs mt-1 font-semibold ${days <= 7 ? 'text-red-600' : 'text-fbslate'}`}>
                  {days > 0 ? `${days} jours restants` : 'Expiré'}
                </p>
              )}
            </div>
          </div>

          {/* Départements */}
          {tender.departments?.length > 0 && (
            <div>
              <h3 className="text-xs font-bold text-fbslate uppercase tracking-widest mb-2">Départements</h3>
              <div className="flex flex-wrap gap-2">
                {tender.departments.map(d => (
                  <span key={d} className="text-sm bg-fbgray text-fbtext px-3 py-1 rounded-pill border border-gray-200 font-medium">
                    {d}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Mots-clés */}
          {tender.matched_keywords?.length > 0 && (
            <div>
              <h3 className="text-xs font-bold text-fbslate uppercase tracking-widest mb-2">Mots-clés détectés</h3>
              <div className="flex flex-wrap gap-2">
                {tender.matched_keywords.map(kw => (
                  <span key={kw} className="text-sm bg-brand-100 text-brand-500 px-3 py-1 rounded-pill font-semibold">
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
                className="flex-1 text-center bg-brand-500 hover:bg-brand-600 text-white font-semibold py-3 rounded-pill transition-all duration-200 tracking-wide text-sm"
              >
                VOIR L'AVIS COMPLET →
              </a>
            )}
            {tender.is_new && (
              <button
                onClick={handleMarkSeen}
                className="flex-1 text-center border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white font-semibold py-3 rounded-pill transition-all duration-200 tracking-wide text-sm"
              >
                MARQUER COMME VU
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
