import { useDropzone } from 'react-dropzone'
import { useCallback } from 'react'
import styles from './UploadZone.module.css'

export default function UploadZone({ onUpload, loading }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onUpload(acceptedFiles[0])
    }
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png'] },
    maxFiles: 1,
    disabled: loading
  })

  return (
    <div className={styles.wrapper}>
      <h2 className={styles.heading}>Upload Chest X-Ray</h2>
      <p className={styles.subheading}>
        Upload a frontal chest X-ray for AI-powered analysis
      </p>

      <div
        {...getRootProps()}
        className={`${styles.dropzone} ${isDragActive ? styles.active : ''} ${loading ? styles.disabled : ''}`}
      >
        <input {...getInputProps()} />
        {loading ? (
          <div className={styles.loadingState}>
            <div className={styles.spinner}></div>
            <p>Analyzing your X-ray...</p>
            <p className={styles.subtext}>This may take 15-30 seconds</p>
          </div>
        ) : isDragActive ? (
          <div className={styles.dragState}>
            <span className={styles.icon}>📂</span>
            <p>Drop the X-ray here</p>
          </div>
        ) : (
          <div className={styles.idleState}>
            <span className={styles.icon}>🩻</span>
            <p className={styles.mainText}>
              Drag & drop your chest X-ray here
            </p>
            <p className={styles.subtext}>or click to browse files</p>
            <div className={styles.formats}>
              Supported: JPG, PNG — Max 10MB
            </div>
          </div>
        )}
      </div>

      <div className={styles.disclaimer}>
        ⚕️ For screening purposes only. Always consult a qualified physician.
      </div>
    </div>
  )
}