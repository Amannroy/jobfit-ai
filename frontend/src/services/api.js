const API_BASE_URL =
  typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL
    ? import.meta.env.VITE_API_BASE_URL
    : 'http://127.0.0.1:8000';

/**
 * Submits resume and job description to the backend analysis endpoint.
 * Notice: We intentionally do NOT set the 'Content-Type' header here so that
 * the browser automatically sets 'multipart/form-data' with the correct boundary.
 */
export async function analyzeJobFit(resumeFile, jobDescription) {
  const formData = new FormData();
  formData.append('resume', resumeFile);
  formData.append('job_description', jobDescription.trim());

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      body: formData,
    });
  } catch (networkError) {
    throw new Error(
      `Unable to connect to the backend server at ${API_BASE_URL}. Please ensure the FastAPI backend is running.`
    );
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMessage = 'An error occurred during analysis.';
    if (data && data.detail) {
      if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMessage = data.detail.map((err) => err.msg || JSON.stringify(err)).join(', ');
      }
    } else {
      errorMessage = `Server responded with HTTP ${response.status} (${response.statusText}).`;
    }
    throw new Error(errorMessage);
  }

  return data;
}
