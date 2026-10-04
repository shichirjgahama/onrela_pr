import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message
    console.error('[API Error]', message)
    return Promise.reject(error)
  },
)
