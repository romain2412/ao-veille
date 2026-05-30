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
  const [selectedTender, setSelectedTender] = useState(null)

  const PAGE_SIZE = 20

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tenders', { page, search, onlyNew, onlyPriority }],
    queryFn: () => getTenders({
      page,
      page_size: PAGE_SIZE,
      search: search || undefined,
      only_new: onlyNew || undefined,
      only_priority: onlyPriority || undefined,
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
    <div className="min-h-screen bg-gray-50">
      <Navbar newCount={data?.total ?? 0} />

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Barre de filtres */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex flex-wrap gap-4 items-center">
          <input
            type="search"
            value={search}
            onChange={handleSearch}
            placeholder="🔍 Rechercher dans les titres…"
            className="flex-1 min-w-[200px] border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input
              type="checkbox"
              checked={onlyNew}
              onChange={e => { setOnlyNew(e.target.checked); setPage(1) }}
              className="accent-brand-500"
            />
            Nouveaux uniquement
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input
              type="checkbox"
              checked={onlyPriority}
              onChange={e => { setOnlyPriority(e.target.checked); setPage(1) }}
              className="accent-brand-500"
            />
            📍 Nouvelle-Aquitaine
          </label>
          {data && (
            <span className="text-sm text-gray-500 ml-auto">
              {data.total} appel{data.total > 1 ? 's' : ''} d'offres
            </span>
          )}
        </div>

        {/* États */}
        {isLoading && (
          <div className="text-center py-20 text-gray-400">Chargement…</div>
        )}
        {isError && (
          <div className="text-center py-20 text-red-500">Erreur de chargement</div>
        )}

        {/* Grille d'AO */}
        {data && (
          <>
            {data.items.length === 0 ? (
              <div className="text-center py-20 text-gray-400">
                Aucun appel d'offres trouvé
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-6">
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
              <div className="flex justify-center items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-40 hover:bg-gray-50"
                >
                  ← Précédent
                </button>
                <span className="text-sm text-gray-600">
                  Page {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 rounded-lg border border-gray-300 text-sm disabled:opacity-40 hover:bg-gray-50"
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
