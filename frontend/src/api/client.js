import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
})

// Injecter le token JWT dans chaque requête
client.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Rediriger vers /login si le token est expiré
client.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default client

// --- Fonctions API ---

export const login = (email, password) =>
  client.post('/auth/login', { email, password }).then(r => r.data)

export const getMe = () =>
  client.get('/auth/me').then(r => r.data)

export const getTenders = (params) =>
  client.get('/tenders', { params }).then(r => r.data)

export const getTender = (id) =>
  client.get(`/tenders/${id}`).then(r => r.data)

export const markSeen = (id) =>
  client.patch(`/tenders/${id}/seen`).then(r => r.data)

export const getTendersStats = () =>
  client.get('/tenders/stats').then(r => r.data)

// --- Admin / monitoring ---

export const getMonitoring = () =>
  client.get('/admin/monitoring').then(r => r.data)

export const triggerCollection = (source) =>
  client.post(`/admin/collect/${source}`).then(r => r.data)

export const getCollectionStatus = (requestId) =>
  client.get(`/admin/collect-status/${requestId}`).then(r => r.data)

export const triggerCollectionAll = () =>
  client.post('/admin/collect-all').then(r => r.data)
