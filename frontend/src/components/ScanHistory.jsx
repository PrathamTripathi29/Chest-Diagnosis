import { useState, useEffect } from 'react'
import { getScanHistory, downloadReport } from '../api'
import styles from './ScanHistory.module.css'

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const URGENCY_COLORS = {
    HIGH: '#fc8181',
    MEDIUM: '#f6ad55',
    LOW: '#68d391'
}

const CONDITION_URGENCY = {
    'Pleural Effusion': 'HIGH',
    'Edema': 'HIGH',
    'Cardiomegaly': 'MEDIUM',
    'No Finding': 'LOW'
}

export default function ScanHistory() {
    const [scans, setScans] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(
        () => {
            fetchHistory()
        }, []
    )

    const fetchHistory = async () => {
        try {
            const res = await getScanHistory()
            setScans(res.data.scans)
        } catch {
            setError('Failed to load scan history')
        } finally {
            setLoading(false)
        }
    }

    const handleDownload = async (scanId) => {
        try {
            const res = await downloadReport(scanId)
            const url = window.URL.createObjectURL(new Blob([res.data]))
            const a = document.createElement('a')
            a.href = url
            a.download = `ChestAI_${scanId}.pdf`
            a.click()
            window.URL.revokeObjectURL(url)
        } catch {
            alert('Download failed. Please try again')
        }
    }

    const getMainFindings = (predictions) => {
    return predictions.filter(p => p.condition !== 'No Finding')
  }

  if (loading) return (
    <div className={styles.wrapper}>
      <h2 className={styles.heading}>Scan History</h2>
      <div className={styles.loadingState}>
        <div className={styles.spinner}></div>
        <p>Loading your scans...</p>
      </div>
    </div>
  )

  if (error) return (
    <div className={styles.wrapper}>
      <h2 className={styles.heading}>Scan History</h2>
      <div className={styles.errorState}>{error}</div>
    </div>
  )

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h2 className={styles.heading}>Scan History</h2>
        <span className={styles.count}>{scans.length} scan{scans.length !== 1 ? 's' : ''}</span>
      </div>

      {scans.length === 0 ? (
        <div className={styles.emptyState}>
          <span className={styles.emptyIcon}>🩻</span>
          <p>No scans yet</p>
          <p className={styles.emptySubtext}>
            Upload a chest X-ray above to get started
          </p>
        </div>
      ) : (
        <div className={styles.scanList}>
          {scans.map((scan) => {
            const findings    = getMainFindings(scan.predictions)
            const hasFindings = findings.length > 0
            return (
              <div key={scan.scan_id} className={styles.scanCard}>
                <div className={styles.scanLeft}>
                  <div className={styles.scanIcon}>
                    {hasFindings ? '⚠️' : '✅'}
                  </div>
                  <div className={styles.scanInfo}>
                    <div className={styles.scanId}>
                      #{scan.scan_id}
                    </div>
                    <div className={styles.scanDate}>
                      {formatDate(scan.created_at)}
                    </div>
                    <div className={styles.findings}>
                      {hasFindings ? (
                        findings.map(pred => (
                          <span
                            key={pred.condition}
                            className={styles.findingTag}
                            style={{
                              background: URGENCY_COLORS[
                                CONDITION_URGENCY[pred.condition] || 'MEDIUM'
                              ] + '33',
                              color: URGENCY_COLORS[
                                CONDITION_URGENCY[pred.condition] || 'MEDIUM'
                              ]
                            }}
                          >
                            {pred.condition} {pred.confidence}%
                          </span>
                        ))
                      ) : (
                        <span
                          className={styles.findingTag}
                          style={{ background: '#68d39133', color: '#68d391' }}
                        >
                          No Findings
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className={styles.scanRight}>
                  {scan.image_url && (
                    <img
                      src={scan.image_url}
                      alt="X-ray thumbnail"
                      className={styles.thumbnail}
                    />
                  )}
                  <button
                    onClick={() => handleDownload(scan.scan_id)}
                    className={styles.downloadBtn}
                  >
                    📄 Report
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}