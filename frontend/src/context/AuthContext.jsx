import { createContext, useContext, useState, useEffect } from 'react'

// Creates a context object — like a global state container
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]     = useState(null)
  const [loading, setLoading] = useState(true)

  // On app load, check if user is already logged in
  // by reading from localStorage
  useEffect(() => {
    const token   = localStorage.getItem('token')
    const userData = localStorage.getItem('user')
    if (token && userData) {
      setUser(JSON.parse(userData))
    }
    setLoading(false)
  }, [])

  const loginUser = (userData, token) => {
    // Save to localStorage so user stays logged in
    // even after browser refresh
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  const logoutUser = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, loginUser, logoutUser }}>
      {children}
    </AuthContext.Provider>
  )
}

// Custom hook — any component can call useAuth()
// to get user, loginUser, logoutUser
export const useAuth = () => useContext(AuthContext)