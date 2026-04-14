import axios from 'axios'

// Base URL from environment variable
const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL
})

// Automatically attach JWT token to every request
// This interceptor runs before every API call
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auth endpoints
export const signup = (data) =>
  API.post('/auth/signup', data)

export const login = (data) =>
  API.post('/auth/login', data)

// Analysis endpoint — sends image file
export const analyzeXray = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return API.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// Chat endpoint
export const sendMessage = (message, conversationHistory, reportData) =>
  API.post('/chat', {
    message,
    conversation_history: conversationHistory,
    report_data: reportData
  })

// History endpoint
export const getScanHistory = () =>
  API.get('/history')

// Report download
export const downloadReport = (scanId) =>
  API.get(`/report/${scanId}`, { responseType: 'blob' })

export default API