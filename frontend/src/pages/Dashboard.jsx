import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { analyzeXray, downloadReport } from '../api'
import Navbar      from '../components/Navbar'
import UploadZone  from '../components/UploadZone'
import ResultsPanel from '../components/ResultsPanel'
import Chatbot     from '../components/Chatbot'
import ScanHistory from '../components/ScanHistory'
import styles      from './Dashboard.module.css'

export default function Dashboard() {
  const { user }    = useAuth()
  const [loading,   setLoading]   = useState(false)
  const [results,   setResults]   = useState(null)
  const [error,     setError]     = useState('')
  const [chatOpen,  setChatOpen]  = useState(false)
  const [historyKey, setHistoryKey] = useState(0)

  const handleUpload = async (file) => {
    setLoading(true)
    setError('')
    setResults(null)

    try {
      const res = await analyzeXray(file)
      setResults(res.data)
      setHistoryKey(prev => prev + 1)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Analysis failed. Please try again with a valid chest X-ray image.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadReport = async () => {
    if (!results?.scan_id) return
    try {
      const res = await downloadReport(results.scan_id)
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a   = document.createElement('a')
      a.href    = url
      a.download = `ChestAI_${results.scan_id}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch {
      alert('Report download failed. Please try again.')
    }
  }

  const reportData = results ? {
    scan_id:     results.scan_id,
    date:        new Date().toLocaleDateString(),
    predictions: results.predictions
  } : null

  return (
    <div className={styles.page}>
      <Navbar />

      <main className={styles.main}>
        <div className={styles.welcome}>
          <h1>Welcome back, {user?.name?.split(' ')[0]} 👋</h1>
          <p>Upload a chest X-ray to get an instant AI-powered analysis</p>
        </div>

        <div className={styles.content}>
          <UploadZone onUpload={handleUpload} loading={loading} />

          {error && (
            <div className={styles.error}>
              ⚠️ {error}
            </div>
          )}

          {results && (
            <ResultsPanel
              results={results}
              onDownloadReport={handleDownloadReport}
              onOpenChat={() => setChatOpen(true)}
            />
          )}

          <ScanHistory key={historyKey} />

        </div>
      </main>

      {chatOpen && results && (
        <Chatbot
          reportData={reportData}
          suggestedQuestions={results.suggested_questions}
          onClose={() => setChatOpen(false)}
        />
      )}
    </div>
  )
}