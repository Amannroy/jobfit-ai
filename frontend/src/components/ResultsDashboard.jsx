import React from 'react';

export default function ResultsDashboard({ analysis, onReset }) {
  if (!analysis) return null;

  const {
    ai_estimated_score = 0,
    score_disclaimer = '',
    summary = '',
    matched_skills = [],
    missing_skills = [],
    tailoring_suggestions = [],
    interview_questions = [],
  } = analysis;

  const getScoreColorClass = (score) => {
    if (score >= 75) return 'score-high';
    if (score >= 50) return 'score-medium';
    return 'score-low';
  };

  const getScoreLabel = (score) => {
    if (score >= 75) return 'Strong Alignment';
    if (score >= 50) return 'Moderate Match';
    return 'Growth Opportunity';
  };

  return (
    <div className="results-wrapper">
      {/* Top Navigation & Score Banner */}
      <div className="results-top-bar">
        <button type="button" className="btn btn-secondary btn-sm" onClick={onReset}>
          ← Analyze Another Resume
        </button>
        <span className="badge">Analysis Complete</span>
      </div>

      {/* Main Score & Disclaimer Card */}
      <section className="card score-hero-card">
        <div className="score-hero-content">
          <div className={`score-circle ${getScoreColorClass(ai_estimated_score)}`}>
            <span className="score-value">{ai_estimated_score}%</span>
            <span className="score-subtext">Estimated Match</span>
          </div>

          <div className="score-info">
            <h2 className="score-title">{getScoreLabel(ai_estimated_score)}</h2>
            <p className="summary-text">{summary}</p>
          </div>
        </div>

        {/* Prominent Disclaimer Banner */}
        <div className="disclaimer-banner" role="note">
          <span className="disclaimer-icon">ℹ️</span>
          <div className="disclaimer-body">
            <strong>AI Guidance Notice: </strong>
            {score_disclaimer ||
              'AI-estimated match score for guidance and preparation only. It does not reflect proprietary ATS algorithms or hiring decisions.'}
          </div>
        </div>
      </section>

      {/* Skills Matrix: Matched vs Missing */}
      <div className="grid skills-grid">
        {/* Matched Skills with Evidence */}
        <section className="card">
          <div className="card-header">
            <h3 className="card-title">
              ✅ Matched Skills <span className="counter-badge success">{matched_skills.length}</span>
            </h3>
          </div>
          <p className="section-desc">Skills identified in both the job description and your resume with supporting evidence.</p>

          {matched_skills.length === 0 ? (
            <p className="empty-state">No direct skill matches identified.</p>
          ) : (
            <ul className="skills-list">
              {matched_skills.map((item, idx) => (
                <li key={idx} className="skill-item matched">
                  <div className="skill-name">{item.skill}</div>
                  <div className="skill-evidence">
                    <span className="evidence-tag">Evidence from Resume:</span>
                    <blockquote>"{item.evidence}"</blockquote>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Missing Skills with Importance & Guidance */}
        <section className="card">
          <div className="card-header">
            <h3 className="card-title">
              ⚠️ Skill & Experience Gaps <span className="counter-badge warning">{missing_skills.length}</span>
            </h3>
          </div>
          <p className="section-desc">Key requirements from the job description not clearly stated in your resume.</p>

          {missing_skills.length === 0 ? (
            <p className="empty-state">No significant skill gaps detected.</p>
          ) : (
            <ul className="skills-list">
              {missing_skills.map((item, idx) => (
                <li key={idx} className="skill-item missing">
                  <div className="skill-header">
                    <span className="skill-name">{item.skill}</span>
                    <span className={`importance-badge ${item.importance?.toLowerCase()}`}>
                      {item.importance === 'required' ? 'Required' : 'Preferred'}
                    </span>
                  </div>
                  {item.guidance && <p className="skill-guidance">{item.guidance}</p>}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Tailoring Suggestions */}
      <section className="card section-margin">
        <div className="card-header">
          <h3 className="card-title">
            ✍️ Evidence-Based Bullet Suggestions <span className="counter-badge primary">{tailoring_suggestions.length}</span>
          </h3>
        </div>
        <p className="section-desc">Actionable rewrites to elevate your bullet points and emphasize measurable results.</p>

        {tailoring_suggestions.length === 0 ? (
          <p className="empty-state">No specific bullet rewrites suggested.</p>
        ) : (
          <div className="suggestions-list">
            {tailoring_suggestions.map((sug, idx) => (
              <div key={idx} className="suggestion-card">
                <div className="suggestion-target">
                  <strong>Target Section: </strong>
                  <span>{sug.target_section}</span>
                </div>
                <div className="suggestion-observation">
                  <strong>Critique: </strong>
                  <span>{sug.observation}</span>
                </div>
                <div className="suggestion-bullet">
                  <strong>Recommended Rewrite:</strong>
                  <p className="bullet-text">“{sug.suggested_bullet}”</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Targeted Interview Questions */}
      <section className="card section-margin">
        <div className="card-header">
          <h3 className="card-title">
            🎯 Targeted Interview Prep <span className="counter-badge info">{interview_questions.length}</span>
          </h3>
        </div>
        <p className="section-desc">Role-specific behavioral and technical questions probing your strengths and gaps.</p>

        {interview_questions.length === 0 ? (
          <p className="empty-state">No interview questions generated.</p>
        ) : (
          <div className="questions-list">
            {interview_questions.map((q, idx) => (
              <div key={idx} className="question-card">
                <div className="question-header">
                  <span className="question-category">{q.category || 'Interview Focus'}</span>
                </div>
                <h4 className="question-text">{q.question}</h4>
                {q.rationale && (
                  <p className="question-rationale">
                    <strong>Why this is asked: </strong>
                    {q.rationale}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Bottom Action Bar */}
      <div className="results-bottom-bar">
        <button type="button" className="btn btn-primary" onClick={onReset}>
          Analyze Another Resume
        </button>
      </div>
    </div>
  );
}
