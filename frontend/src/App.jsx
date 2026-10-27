import React, { useState, useRef } from 'react';
import { analyzeJobFit } from './services/api';
import ResultsDashboard from './components/ResultsDashboard';

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const MIN_JD_LENGTH = 50;

const SAMPLE_JOB_DESCRIPTION = `We are seeking an experienced Full Stack Software Engineer to build and scale web applications.
Key Requirements:
- 3+ years experience with Python, FastAPI, and React.
- Strong knowledge of RESTful APIs, asynchronous patterns, and SQL/NoSQL databases.
- Familiarity with Docker containerization and modern CI/CD deployment pipelines.
- Excellent communication and collaborative problem-solving skills.`;

export default function App() {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Handle PDF file selection
  const handleFileChange = (selectedFile) => {
    setError('');

    if (!selectedFile) return;

    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Invalid file type. Please upload a PDF document (.pdf).');
      setFile(null);
      return;
    }

    if (selectedFile.size > MAX_FILE_SIZE_BYTES) {
      const sizeMB = (selectedFile.size / (1024 * 1024)).toFixed(2);
      setError(`File is too large (${sizeMB} MB). Maximum allowed size is 5 MB.`);
      setFile(null);
      return;
    }

    setFile(selectedFile);
  };

  // Drag-and-drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    if (!isLoading) setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (!isLoading && e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  // Form submission -> calls backend API
  const handleAnalyzeClick = async (e) => {
    e.preventDefault();
    if (isLoading) return; // Prevent duplicate submissions

    setError('');

    if (!file) {
      setError('Please select or upload a resume in PDF format.');
      return;
    }

    const cleanJD = jobDescription.trim();
    if (cleanJD.length < MIN_JD_LENGTH) {
      setError(
        `Job description is too short (${cleanJD.length} characters). Please provide at least ${MIN_JD_LENGTH} characters for an accurate analysis.`
      );
      return;
    }

    setIsLoading(true);

    try {
      const result = await analyzeJobFit(file, cleanJD);
      setAnalysis(result);
    } catch (err) {
      setError(err.message || 'An unexpected error occurred during analysis.');
    } finally {
      setIsLoading(false);
    }
  };

  // Reset form and return from results view
  const handleReset = () => {
    setFile(null);
    setJobDescription('');
    setError('');
    setAnalysis(null);
    setIsLoading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const isJDValid = jobDescription.trim().length >= MIN_JD_LENGTH;

  return (
    <div className="container">
      {/* Header */}
      <header className="header">
        <span className="badge">JobFit AI</span>
        <h1 className="title">Resume & Job Fit Analyzer</h1>
        <p className="subtitle">
          Evaluate resume alignment against target job descriptions using Gemini structured analysis.
        </p>
      </header>

      {/* Alert Notices */}
      {error && (
        <div className="alert alert-error" role="alert">
          <span className="alert-icon">⚠️</span>
          <div className="alert-text">{error}</div>
        </div>
      )}

      {/* If analysis is available, render the Results Dashboard */}
      {analysis ? (
        <ResultsDashboard analysis={analysis} onReset={handleReset} />
      ) : (
        /* Otherwise render the Input Form */
        <form onSubmit={handleAnalyzeClick}>
          <div className="grid">
            {/* Card 1: Resume PDF Upload */}
            <div className="card">
              <div className="card-header">
                <h2 className="card-title">📄 Resume Upload</h2>
                <span className="card-hint">PDF up to 5 MB</span>
              </div>

              <input
                type="file"
                ref={fileInputRef}
                accept=".pdf,application/pdf"
                style={{ display: 'none' }}
                disabled={isLoading}
                onChange={(e) => handleFileChange(e.target.files[0])}
              />

              <div
                className={`dropzone ${isDragging ? 'active' : ''} ${isLoading ? 'disabled' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => !isLoading && fileInputRef.current?.click()}
              >
                <div className="dropzone-icon">📤</div>
                <div className="dropzone-label">
                  {file ? 'Click or drop to replace PDF' : 'Click to upload or drag & drop'}
                </div>
                <div className="dropzone-sublabel">Text-searchable PDF only (max 5 MB)</div>
              </div>

              {file && (
                <div className="file-info">
                  <div>
                    <div className="file-name" title={file.name}>
                      {file.name}
                    </div>
                    <div className="file-size">{formatFileSize(file.size)}</div>
                  </div>
                  {!isLoading && (
                    <button
                      type="button"
                      className="btn-sample"
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                    >
                      Remove
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Card 2: Job Description Input */}
            <div className="card">
              <div className="card-header">
                <h2 className="card-title">📝 Job Description</h2>
                <button
                  type="button"
                  className="btn-sample"
                  disabled={isLoading}
                  onClick={() => setJobDescription(SAMPLE_JOB_DESCRIPTION)}
                >
                  Load Sample JD
                </button>
              </div>

              <div className="textarea-wrapper">
                <textarea
                  className="textarea"
                  placeholder="Paste the target job description requirements, responsibilities, and qualifications here..."
                  value={jobDescription}
                  disabled={isLoading}
                  onChange={(e) => setJobDescription(e.target.value)}
                />

                <div className="textarea-footer">
                  <span className={`char-counter ${isJDValid ? 'valid' : ''}`}>
                    {jobDescription.trim().length} / {MIN_JD_LENGTH} min characters
                  </span>
                  {isJDValid && <span className="card-hint">✓ Meets length requirement</span>}
                </div>
              </div>
            </div>
          </div>

          {/* Loading Indicator */}
          {isLoading && (
            <div className="loading-container">
              <div className="spinner"></div>
              <div className="loading-content">
                <strong>Analyzing Resume with Gemini...</strong>
                <p className="loading-subtext">
                  Parsing in memory, evaluating role alignment, and generating evidence-backed suggestions. This usually takes 3–5 seconds.
                </p>
              </div>
            </div>
          )}

          {/* Actions Bar */}
          <div className="actions">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={isLoading}
              onClick={handleReset}
            >
              Reset
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!file || !isJDValid || isLoading}
            >
              {isLoading ? (
                <>
                  <span className="spinner-btn"></span>
                  Analyzing...
                </>
              ) : (
                '🔍 Analyze Fit'
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
