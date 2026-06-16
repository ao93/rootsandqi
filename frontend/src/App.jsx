import { useState } from 'react'
import styles from './App.module.css'

const SYNDROME_LABELS = {
  qi_deficiency: 'Qi Deficiency',
  blood_deficiency: 'Blood Deficiency',
  yin_deficiency: 'Yin Deficiency',
  yang_deficiency: 'Yang Deficiency',
  dampness: 'Dampness',
  heat_damp_heat: 'Damp-Heat',
  cold: 'Cold',
  qi_stagnation: 'Qi Stagnation',
  blood_stasis: 'Blood Stasis',
  spleen_qi_deficiency: 'Spleen Qi Deficiency',
}

function ConfidenceBar({ value }) {
  const pct = Math.round(value * 100)
  return (
    <div className={styles.confidenceWrap}>
      <div className={styles.confidenceLabel}>
        <span>Confidence</span>
        <span>{pct}%</span>
      </div>
      <div className={styles.confidenceTrack}>
        <div
          className={styles.confidenceFill}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function HerbCard({ rec }) {
  const isIndigenous = rec.herb.tradition.toLowerCase().includes('indigenous')
  const isShared = rec.herb.tradition.toLowerCase().includes('shared')
  const tradClass = isShared
    ? styles.herbShared
    : isIndigenous
    ? styles.herbIndigenous
    : styles.herbTCM
  const tradLabel = isShared
    ? 'Shared Tradition'
    : isIndigenous
    ? 'Indigenous'
    : 'TCM'

  return (
    <div className={`${styles.herbCard} ${tradClass}`}>
      <div className={styles.herbHeader}>
        <span className={styles.herbName}>{rec.herb.name}</span>
        <span className={styles.herbTrad}>{tradLabel}</span>
      </div>
      <p className={styles.herbDesc}>{rec.herb.description}</p>
      <div className={styles.herbMeta}>
        <div className={styles.herbMetaRow}>
          <span className={styles.herbMetaLabel}>Preparation</span>
          <span>{rec.herb.preparation}</span>
        </div>
        <div className={styles.herbMetaRow}>
          <span className={styles.herbMetaLabel}>Cautions</span>
          <span>{rec.herb.cautions}</span>
        </div>
      </div>
    </div>
  )
}

function Results({ data }) {
  const { classification, herb_recommendations, disclaimer } = data
  const primaryLabel = SYNDROME_LABELS[classification.primary_pattern] || classification.primary_pattern
  const secondaryLabels = classification.secondary_patterns
    .map(p => SYNDROME_LABELS[p] || p)
    .join(', ')

  const tcmHerbs = herb_recommendations.filter(r =>
    r.herb.tradition.toLowerCase().includes('tcm')
  )
  const indigenousHerbs = herb_recommendations.filter(r =>
    r.herb.tradition.toLowerCase().includes('indigenous')
  )
  const sharedHerbs = herb_recommendations.filter(r =>
    r.herb.tradition.toLowerCase().includes('shared')
  )

  return (
    <div className={styles.results}>
      <div className={styles.resultsDivider}>
        <span>Diagnostic Results</span>
      </div>

      <div className={styles.syndromeCard}>
        <div className={styles.syndromeHeader}>
          <div>
            <div className={styles.syndromeEyebrow}>Primary Pattern</div>
            <div className={styles.syndromeName}>{primaryLabel}</div>
            {secondaryLabels && (
              <div className={styles.syndromeSecondary}>
                Also: {secondaryLabels}
              </div>
            )}
          </div>
          <div className={styles.syndromeOrgans}>
            {classification.affected_organs.map(o => (
              <span key={o} className={styles.organTag}>{o}</span>
            ))}
          </div>
        </div>
        <ConfidenceBar value={classification.confidence} />
        <p className={styles.syndromeReasoning}>{classification.reasoning}</p>
      </div>

      {herb_recommendations.length > 0 && (
        <div className={styles.herbsSection}>
          <h3 className={styles.herbsTitle}>Herb Recommendations</h3>
          <p className={styles.herbsSubtitle}>
            Drawn from Traditional Chinese Medicine and Indigenous herbal traditions
          </p>

          <div className={styles.herbColumns}>
            {tcmHerbs.length > 0 && (
              <div className={styles.herbColumn}>
                <div className={`${styles.herbColumnLabel} ${styles.herbColumnLabelTCM}`}>
                  Traditional Chinese Medicine
                </div>
                {tcmHerbs.map(r => (
                  <HerbCard key={r.herb.id} rec={r} />
                ))}
              </div>
            )}
            {(indigenousHerbs.length > 0 || sharedHerbs.length > 0) && (
              <div className={styles.herbColumn}>
                <div className={`${styles.herbColumnLabel} ${styles.herbColumnLabelIndigenous}`}>
                  Indigenous &amp; Shared Traditions
                </div>
                {indigenousHerbs.map(r => (
                  <HerbCard key={r.herb.id} rec={r} />
                ))}
                {sharedHerbs.map(r => (
                  <HerbCard key={r.herb.id} rec={r} />
                ))}
              </div>
            )}
          </div>

          {tcmHerbs.length > 0 && indigenousHerbs.length === 0 && sharedHerbs.length === 0 && (
            <p className={styles.noIndigenousNote}>
              No Indigenous herbs matched this pattern closely in this run.
              Herb retrieval is probabilistic — try again or add more herbs to the knowledge base.
            </p>
          )}
        </div>
      )}

      <p className={styles.disclaimer}>{disclaimer}</p>
    </div>
  )
}

export default function App() {
  const [symptoms, setSymptoms] = useState('')
  const [tongue, setTongue] = useState({
    color: '',
    coating: '',
    shape: '',
    moisture: '',
  })
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [showTongue, setShowTongue] = useState(false)

  const hasTongueData = Object.values(tongue).some(v => v.trim())

  async function handleSubmit(e) {
    e.preventDefault()
    if (!symptoms.trim()) return
    setLoading(true)
    setResults(null)
    setError(null)

    const body = {
      symptoms: symptoms.trim(),
      ...(hasTongueData && {
        tongue_observation: {
          color: tongue.color || 'not observed',
          coating: tongue.coating || 'not observed',
          shape: tongue.shape || 'not observed',
          moisture: tongue.moisture || 'not observed',
        }
      })
    }

    try {
      const res = await fetch('/diagnose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Server error ${res.status}`)
      }
      const data = await res.json()
      setResults(data)
      setTimeout(() => {
        document.getElementById('results-anchor')?.scrollIntoView({ behavior: 'smooth' })
      }, 100)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <div className={styles.heroInner}>
          <div className={styles.logoMark}>⟐</div>
          <h1 className={styles.heroTitle}>RootsAndQi</h1>
          <p className={styles.heroTagline}>
            Wellness insights at the intersection of Traditional Chinese Medicine
            and Indigenous herbal traditions
          </p>
        </div>
      </header>

      <main className={styles.main}>
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.formCard}>
            <label className={styles.label} htmlFor="symptoms">
              Describe your symptoms
            </label>
            <textarea
              id="symptoms"
              className={styles.textarea}
              value={symptoms}
              onChange={e => setSymptoms(e.target.value)}
              placeholder="e.g. I feel tired all the time, especially in the afternoon. I bruise easily and feel cold."
              rows={4}
              required
            />

            <button
              type="button"
              className={styles.tongueToggle}
              onClick={() => setShowTongue(v => !v)}
            >
              {showTongue ? '▲ Hide' : '▼ Add'} tongue observation{' '}
              <span className={styles.optional}>(optional)</span>
            </button>

            {showTongue && (
              <div className={styles.tongueGrid}>
                {[
                  ['color', 'Tongue color', 'e.g. pale, red, purple'],
                  ['coating', 'Coating', 'e.g. thin white, thick yellow, none'],
                  ['shape', 'Shape', 'e.g. swollen, thin, tooth marks on sides'],
                  ['moisture', 'Moisture', 'e.g. dry, normal, wet'],
                ].map(([key, label, placeholder]) => (
                  <div key={key} className={styles.tongueField}>
                    <label className={styles.tongueLabel}>{label}</label>
                    <input
                      type="text"
                      className={styles.input}
                      value={tongue[key]}
                      onChange={e => setTongue(t => ({ ...t, [key]: e.target.value }))}
                      placeholder={placeholder}
                    />
                  </div>
                ))}
              </div>
            )}

            <button
              type="submit"
              className={styles.submitBtn}
              disabled={loading || !symptoms.trim()}
            >
              {loading ? (
                <span className={styles.loadingDots}>Analysing<span>.</span><span>.</span><span>.</span></span>
              ) : (
                'Get Wellness Insights'
              )}
            </button>

            {error && (
              <div className={styles.error}>
                <strong>Error:</strong> {error}. Make sure the RootsAndQi API is running on port 8000.
              </div>
            )}
          </div>
        </form>

        <div id="results-anchor" />
        {results && <Results data={results} />}
      </main>

      <footer className={styles.footer}>
        <p>
          RootsAndQi is an educational tool only. Not a substitute for professional medical advice.
        </p>
      </footer>
    </div>
  )
}
