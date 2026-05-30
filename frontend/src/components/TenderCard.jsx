import { markSeen } from '../api/client'
import { useQueryClient } from '@tanstack/react-query'

const DEPT_NAMES = {
  '16': 'Charente', '17': 'Charente-Maritime', '19': 'Corrèze',
  '23': 'Creuse', '24': 'Dordogne', '33': 'Gironde', '40': 'Landes',
  '47': 'Lot-et-Garonne', '64': 'Pyrénées-Atl.', '79': 'Deux-Sèvres',
  '86': 'Vienne', '87': 'Haute-Vienne',
}

function ScoreBadge({ score }) {
  const color =
    score >= 70 ? 'bg-green-100 text-green-800' :
    score >= 40 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-600'
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${color}`}>
      {score} pts
    </span>
  )
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function daysLeft(iso) {
  if (!iso) return null
  const diff = Math.ceil((new Date(iso) - new Date()) / 86400000)
  return diff
}

export default function TenderCard({ tender, onClick }) {
  const queryClient = useQueryClient()
  const days = daysLeft(tender.deadline)

  const handleMarkSeen = async e => {
    e.stopPropagation()
    await markSeen(tender.id)
    queryClient.invalidateQueries({ queryKey: ['tenders'] })
  }

  return (
    <div
      onClick={() => onClick(tender)}
      className={`bg-white rounded-xl border cursor-pointer hover:shadow-md transition-all ${
        tender.is_new ? 'border-brand-500 border-l-4' : 'border-gray-200'
      }`}
    >
      <div className="p-4">
        {/* En-tête */}
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2 flex-wrap">
            {tender.is_new && (
              <span className="bg-brand-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                NOUVEAU
              </span>
            )}
            {tender.is_priority_region && (
              <span className="bg-blue-100 text-blue-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                📍 Nouv.-Aquitaine
              </span>
            )}
            <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">
              {tender.market_type}
            </span>
          </div>
          <ScoreBadge score={tender.score} />
        </div>

        {/* Titre */}
        <h3 className="font-semibold text-gray-800 text-sm leading-snug mb-2 line-clamp-2">
          {tender.title}
        </h3>

        {/* Acheteur */}
        {tender.buyer_name && (
          <p className="text-xs text-gray-500 mb-2">🏛 {tender.buyer_name}</p>
        )}

        {/* Départements */}
        {tender.departments?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {tender.departments.slice(0, 4).map(d => (
              <span key={d} className="text-xs bg-gray-50 border border-gray-200 px-2 py-0.5 rounded">
                {d} {DEPT_NAMES[d] ? `— ${DEPT_NAMES[d]}` : ''}
              </span>
            ))}
          </div>
        )}

        {/* Mots-clés */}
        {tender.matched_keywords?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {tender.matched_keywords.slice(0, 5).map(kw => (
              <span key={kw} className="text-xs bg-brand-50 text-brand-700 border border-brand-100 px-2 py-0.5 rounded">
                {kw}
              </span>
            ))}
          </div>
        )}

        {/* Pied de carte */}
        <div className="flex items-center justify-between pt-2 border-t border-gray-100">
          <div className="text-xs text-gray-400">
            Publié le {formatDate(tender.publication_date)}
          </div>
          <div className="flex items-center gap-2">
            {days !== null && (
              <span className={`text-xs font-medium ${
                days <= 7 ? 'text-red-600' : days <= 14 ? 'text-orange-500' : 'text-gray-500'
              }`}>
                {days > 0 ? `⏱ ${days}j restants` : '⚠️ Expiré'}
              </span>
            )}
            {tender.is_new && (
              <button
                onClick={handleMarkSeen}
                className="text-xs text-gray-400 hover:text-brand-500 underline"
              >
                Marquer vu
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
