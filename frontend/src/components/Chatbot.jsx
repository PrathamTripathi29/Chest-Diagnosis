import { useState, useRef, useEffect } from 'react'
import { sendMessage } from '../api'
import styles from './Chatbot.module.css'

export default function Chatbot({ reportData, suggestedQuestions, onClose }) {
  const [messages,    setMessages]    = useState([{
    role: 'model',
    content: `Hi! I'm your AI assistant for this scan. I can help you understand your results. What would you like to know?`
  }])
  const [input,       setInput]       = useState('')
  const [loading,     setLoading]     = useState(false)
  const [history,     setHistory]     = useState([])
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (text) => {
    const message = text || input.trim()
    if (!message || loading) return

    setMessages(prev => [...prev, { role: 'user', content: message }])
    setInput('')
    setLoading(true)

    try {
      const res = await sendMessage(message, history, reportData)
      const botReply = res.data.response
      setMessages(prev => [...prev, { role: 'model', content: botReply }])
      setHistory(res.data.conversation_history)
    } catch {
      setMessages(prev => [...prev, {
        role: 'model',
        content: 'Sorry, I encountered an error. Please try again.'
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.panel}>
        <div className={styles.header}>
          <div>
            <h3 className={styles.title}>💬 AI Assistant</h3>
            <p className={styles.subtitle}>Ask about your scan results</p>
          </div>
          <button onClick={onClose} className={styles.closeBtn}>✕</button>
        </div>

        <div className={styles.messages}>
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`${styles.message} ${msg.role === 'user' ? styles.userMsg : styles.botMsg}`}
            >
              {msg.role === 'model' && <span className={styles.avatar}>🤖</span>}
              <div className={styles.bubble}>{msg.content}</div>
            </div>
          ))}
          {loading && (
            <div className={`${styles.message} ${styles.botMsg}`}>
              <span className={styles.avatar}>🤖</span>
              <div className={styles.bubble}>
                <span className={styles.typing}>
                  <span/><span/><span/>
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {suggestedQuestions?.length > 0 && history.length === 0 && (
          <div className={styles.suggestions}>
            <p className={styles.suggestLabel}>Suggested questions:</p>
            <div className={styles.suggestionBtns}>
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  className={styles.suggestionBtn}
                  onClick={() => handleSend(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className={styles.inputArea}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Ask about your results..."
            className={styles.input}
            disabled={loading}
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className={styles.sendBtn}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}