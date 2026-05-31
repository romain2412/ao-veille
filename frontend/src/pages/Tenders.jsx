import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getTenders } from '../api/client'
import Navbar from '../components/Navbar'
import TenderCard from '../components/TenderCard'
import TenderDetail from '../components/TenderDetail'

export default function Tenders() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [onlyNew, setOnlyNew] = useState(false)
  const [onlyPriority, setOnlyPriority] = useState(false)
  const [selectedSources, setSelectedSources] = useState(['boamp', 'demat_ampa', 'e_marches_publics', 'noalis'])
  const [selectedTender, setSelectedTender] = useState(null)

  const ALL_SOURCES = [
    { key: 'boamp', label: 'BOAMP', color: 'bg-blue-100 text-blue-700 border-blue-200' },
    { key: 'demat_ampa', label: 'AMPA', color: 'bg-purple-100 text-purple-700 border-purple-200' },
    { key: 'e_marches_publics', label: 'e-MP', color: 'bg-orange-100 text-orange-700 border-orange-200' },
    { key: 'noalis', label: 'Noalis', color: 'bg-green-100 text-green-700 border-green-200' },
  ]

  const toggleSource = (src) => {
    setSelectedSources(prev =>
      prev.includes(src)
        ? prev.filter(s => s !== src)
        : [...prev, src]
    )
    setPage(1)
  }

  const PAGE_SIZE = 20

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tenders', { page, search, onlyNew, onlyPriority, selectedSources }],
    queryFn: () => getTenders({
      page,
      page_size: PAGE_SIZE,
      search: search || undefined,
      only_new: onlyNew || undefined,
      only_priority: onlyPriority || undefined,
      sources: selectedSources.length > 0 ? selectedSources.join(',') : undefined,
    }),
    keepPreviousData: true,
  })

  const newCount = data?.items?.filter(t => t.is_new).length ?? 0
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1

  const handleSearch = e => {
    setSearch(e.target.value)
    setPage(1)
  }

  return (
    <div className="min-h-screen bg-fbgray">
      <Navbar totalCount={data?.total ?? 0} newCount={newCount} />

      <div className="max-w-7xl mx-auto px-4 py-8">

        {/* Barre de filtres */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6 flex flex-wrap gap-4 items-center shadow-sm">
          <input
            type="search"
            value={search}
            onChange={handleSearch}
            placeholder="Rechercher dans les titres…"
            className="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-4 py-2.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />

          <label className="flex items-center gap-2 text-sm font-semibold cursor-pointer select-none text-fbtext">
            <input
              type="checkbox"
              checked={onlyNew}
              onChange={e => { setOnlyNew(e.target.checked); setPage(1) }}
              className="w-4 h-4 accent-brand-500 rounded"
            />
            Nouveaux uniquement
          </label>

          <label className="flex items-center gap-2 text-sm font-semibold cursor-pointer select-none text-fbtext">
            <input
              type="checkbox"
              checked={onlyPriority}
              onChange={e => { setOnlyPriority(e.target.checked); setPage(1) }}
              className="w-4 h-4 accent-brand-500 rounded"
            />
            📍 Nouvelle-Aquitaine
          </label>

          {/* Filtre sources */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-fbslate uppercase tracking-wide">Sources :</span>
            {ALL_SOURCES.map(src => (
              <button
                key={src.key}
                onClick={() => toggleSource(src.key)}
                className={`text-xs font-bold px-3 py-1 rounded-pill border transition-all duration-200 ${
                  selectedSources.includes(src.key)
                    ? src.color
                    : 'bg-white text-gray-400 border-gray-200 opacity-50'
                }`}
              >
                {src.label}
              </button>
            ))}
          </div>

          {data && (
            <div className="ml-auto text-right">
              <span className="text-sm font-semibold text-brand-500">
                {data.total} appel{data.total > 1 ? 's' : ''} d'offres
              </span>
              {newCount > 0 && (
                <span className="ml-2 bg-brand-500 text-white text-xs font-bold px-2 py-0.5 rounded-pill">
                  {newCount} nouveau{newCount > 1 ? 'x' : ''}
                </span>
              )}
            </div>
          )}
        </div>

        {/* États */}
        {isLoading && (
          <div className="text-center py-20 text-fbslate font-medium">Chargement…</div>
        )}
        {isError && (
          <div className="text-center py-20 text-red-500 font-medium">Erreur de chargement</div>
        )}

        {/* Grille */}
        {data && (
          <>
            {data.items.length === 0 ? (
              <div className="text-center py-20">
                <p className="text-fbslate font-medium">Aucun appel d'offres trouvé</p>
                <p className="text-fbslate text-sm mt-1">Modifiez les filtres ou attendez la prochaine collecte</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
                {data.items.map(tender => (
                  <TenderCard
                    key={tender.id}
                    tender={tender}
                    onClick={setSelectedTender}
                  />
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center gap-3">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white font-semibold px-6 py-2 rounded-pill text-sm transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  ← Précédent
                </button>
                <span className="text-sm font-medium text-fbslate">
                  Page {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="border border-brand-500 text-brand-500 hover:bg-brand-500 hover:text-white font-semibold px-6 py-2 rounded-pill text-sm transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Suivant →
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modale détail */}
      {selectedTender && (
        <TenderDetail
          tender={selectedTender}
          onClose={() => setSelectedTender(null)}
        />
      )}
    </div>
  )
}
