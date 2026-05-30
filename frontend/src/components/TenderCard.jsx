import { markSeen } from '../api/client'
import { useQueryClient } from '@tanstack/react-query'

const SOURCE_LABELS = {
  boamp: 'BOAMP',
  demat_ampa: 'AMPA',
  e_marches_publics: 'e-MP',
}

const SOURCE_COLORS = {
  boamp: 'bg-blue-100 text-blue-700',
  demat_ampa: 'bg-purple-100 text-purple-700',
  e_marches_publics: 'bg-orange-100 text-orange-700',
}

const DEPT_NAMES = {
  '16': 'Charente', '17': 'Charente-Maritime', '19': 'Corrèze',
  '23': 'Creuse', '24': 'Dordogne', '33': 'Gironde', '40': 'Landes',
  '47': 'Lot-et-Garonne', '64': 'Pyrénées-Atl.', '79': 'Deux-Sèvres',
  '86': 'Vienne', '87': 'Haute-Vienne',
}

function ScoreBadge({ score }) {
  const color =
    score >= 70 ? 'bg-brand-500 text-white' :
    score >= 40 ? 'bg-brand-100 text-brand-500' :
                  'bg-gray-100 text-fbslate'
  return (
    <span className={`text-xs font-bold px-3 py-0.5 rounded-pill ${color}`}>
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
  return Math.ceil((new Date(iso) - new Date()) / 86400000)
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
      className={`bg-white rounded-xl cursor-pointer hover:shadow-lg transition-all duration-200 border ${
        tender.is_new
          ? 'border-l-4 border-brand-500 shadow-sm'
          : 'border-gray-200 hover:border-brand-100'
      }`}
    >
      <div className="p-5">
        {/* Badges */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            {tender.is_new && (
              <span className="bg-brand-500 text-white text-xs font-bold px-3 py-0.5 rounded-pill tracking-wide">
                NOUVEAU
              </span>
            )}
            {tender.is_priority_region && (
              <span className="bg-brand-100 text-brand-500 text-xs font-semibold px-2 py-0.5 rounded-pill">
                📍 Nouv.-Aquitaine
              </span>
            )}
            <span className="bg-fbgray text-fbslate text-xs font-medium px-2 py-0.5 rounded-pill">
              {tender.market_type}
            </span>
            {/* Badges sources */}
            {(tender.sources || [tender.source]).map(src => (
              <span
                key={src}
                className={`text-xs font-semibold px-2 py-0.5 rounded-pill ${SOURCE_COLORS[src] || 'bg-gray-100 text-gray-600'}`}
              >
                {SOURCE_LABELS[src] || src.toUpperCase()}
              </span>
            ))}
          </div>
          <ScoreBadge score={tender.score} />
        </div>

        {/* Titre */}
        <h3 className="font-semibold text-fbtext text-sm leading-snug mb-2 line-clamp-2">
          {tender.title}
        </h3>

        {/* Acheteur */}
        {tender.buyer_name && (
          <p className="text-xs text-fbslate mb-3 font-medium">🏛 {tender.buyer_name}</p>
        )}

        {/* Départements */}
        {tender.departments?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {tender.departments.slice(0, 4).map(d => (
              <span key={d} className="text-xs bg-fbgray text-fbslate px-2 py-0.5 rounded-lg border border-gray-200">
                {d}{DEPT_NAMES[d] ? ` · ${DEPT_NAMES[d]}` : ''}
              </span>
            ))}
          </div>
        )}

        {/* Mots-clés */}
        {tender.matched_keywords?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {tender.matched_keywords.slice(0, 4).map(kw => (
              <span key={kw} className="text-xs bg-brand-100 text-brand-500 px-2 py-0.5 rounded-lg font-medium">
                {kw}
              </span>
            ))}
          </div>
        )}

        {/* Pied */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100 mt-3">
          <span className="text-xs text-fbslate">
            {formatDate(tender.publication_date)}
          </span>
          <div className="flex items-center gap-3">
            {days !== null && (
              <span className={`text-xs font-semibold ${
                days <= 7 ? 'text-red-600' : days <= 14 ? 'text-orange-500' : 'text-fbslate'
              }`}>
                {days > 0 ? `⏱ ${days}j` : '⚠️ Expiré'}
              </span>
            )}
            {tender.is_new && (
              <button
                onClick={handleMarkSeen}
                className="text-xs text-fbslate hover:text-brand-500 font-medium transition-colors"
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
