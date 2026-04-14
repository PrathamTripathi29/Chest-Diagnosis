import styles from './ResultsPanel.module.css'

const URGENCY_COLORS = {
  HIGH:   { bg: '#fff5f5', border: '#feb2b2', text: '#c53030', badge: '#fc8181' },
  MEDIUM: { bg: '#fffaf0', border: '#fbd38d', text: '#c05621', badge: '#f6ad55' },
  LOW:    { bg: '#f0fff4', border: '#9ae6b4', text: '#276749', badge: '#68d391' }
}

const CONDITION_URGENCY = {
  'Pleural Effusion': 'HIGH',
  'Edema':            'HIGH',
  'Cardiomegaly':     'MEDIUM',
  'No Finding':       'LOW'
}

export default function ResultsPanel({ results, onDownloadReport, onOpenChat }) {
  const { predictions, heatmaps, scan_id, has_findings } = results

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Analysis Results</h2>
          <p className={styles.scanId}>Scan ID: #{scan_id}</p>
        </div>
        <div className={styles.actions}>
          <button onClick={onDownloadReport} className={styles.reportBtn}>
            📄 Download Report
          </button>
          <button onClick={onOpenChat} className={styles.chatBtn}>
            💬 Ask AI
          </button>
        </div>
      </div>

      {!has_findings ? (
        <div className={styles.normalResult}>
          <span className={styles.normalIcon}>✅</span>
          <h3>No Significant Findings</h3>
          <p>Your chest X-ray appears within normal limits.</p>
          <p className={styles.normalDisclaimer}>
            Always confirm with a qualified radiologist.
          </p>
        </div>
      ) : (
        <div className={styles.findings}>
          {predictions
            .filter(p => p.condition !== 'No Finding')
            .map((pred) => {
              const urgency = CONDITION_URGENCY[pred.condition] || 'MEDIUM'
              const colors  = URGENCY_COLORS[urgency]
              return (
                <div
                  key={pred.condition}
                  className={styles.findingCard}
                  style={{ background: colors.bg, borderColor: colors.border }}
                >
                  <div className={styles.findingHeader}>
                    <div>
                      <h3 className={styles.conditionName}>{pred.condition}</h3>
                      <span
                        className={styles.urgencyBadge}
                        style={{ background: colors.badge, color: colors.text }}
                      >
                        {urgency} URGENCY
                      </span>
                    </div>
                    <div className={styles.confidence}>
                      <span
                        className={styles.confidenceNumber}
                        style={{ color: colors.text }}
                      >
                        {pred.confidence}%
                      </span>
                      <span className={styles.confidenceLabel}>confidence</span>
                    </div>
                  </div>

                  <div className={styles.progressBar}>
                    <div
                      className={styles.progressFill}
                      style={{
                        width: `${pred.confidence}%`,
                        background: colors.badge
                      }}
                    />
                  </div>

                  {heatmaps[pred.condition] && (
                    <div className={styles.heatmapSection}>
                      <p className={styles.heatmapLabel}>
                        🔍 Region of Interest (Grad-CAM)
                      </p>
                      <img
                        src={`data:image/png;base64,${heatmaps[pred.condition]}`}
                        alt={`Heatmap for ${pred.condition}`}
                        className={styles.heatmap}
                      />
                      <p className={styles.heatmapCaption}>
                        Red areas indicate where the model focused for this finding
                      </p>
                    </div>
                  )}
                </div>
              )
            })}
        </div>
      )}
    </div>
  )
}