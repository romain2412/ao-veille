// Définition centralisée des sources/collecteurs (libellés + couleurs).
// Source de vérité unique partagée par toutes les pages/composants.

// Libellés courts affichés dans l'UI
export const SOURCE_LABELS = {
  boamp: 'BOAMP',
  demat_ampa: 'AMPA',
  e_marches_publics: 'e-MP',
  noalis: 'Noalis',
  vilogia: 'Vilogia',
  aquitanis: 'Aquitanis',
}

// Couleurs "badge" (sans bordure) — utilisées pour les pastilles de source
export const SOURCE_COLORS = {
  boamp: 'bg-blue-100 text-blue-700',
  demat_ampa: 'bg-purple-100 text-purple-700',
  e_marches_publics: 'bg-orange-100 text-orange-700',
  noalis: 'bg-green-100 text-green-700',
  vilogia: 'bg-red-100 text-red-700',
  aquitanis: 'bg-teal-100 text-teal-700',
}

// Couleurs "carte" (avec bordure) — utilisées pour les cartes cliquables/filtres
export const SOURCE_COLORS_BORDERED = {
  boamp: 'bg-blue-100 text-blue-700 border-blue-200',
  demat_ampa: 'bg-purple-100 text-purple-700 border-purple-200',
  e_marches_publics: 'bg-orange-100 text-orange-700 border-orange-200',
  noalis: 'bg-green-100 text-green-700 border-green-200',
  vilogia: 'bg-red-100 text-red-700 border-red-200',
  aquitanis: 'bg-teal-100 text-teal-700 border-teal-200',
}

// Ordre canonique des sources (clés)
export const SOURCE_KEYS = [
  'boamp', 'demat_ampa', 'e_marches_publics', 'noalis', 'vilogia', 'aquitanis',
]

// Liste prête à l'emploi pour le bandeau de filtres (clé, libellé, couleur bordée)
export const ALL_SOURCES = SOURCE_KEYS.map(key => ({
  key,
  label: SOURCE_LABELS[key],
  color: SOURCE_COLORS_BORDERED[key],
}))

// Helpers de fallback (source inconnue)
export const sourceLabel = (key) => SOURCE_LABELS[key] || (key || '').toUpperCase()
export const sourceColor = (key) => SOURCE_COLORS[key] || 'bg-gray-100 text-gray-600'
export const sourceColorBordered = (key) =>
  SOURCE_COLORS_BORDERED[key] || 'bg-gray-100 text-gray-600 border-gray-200'
