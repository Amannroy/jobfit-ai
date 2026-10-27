import test from 'node:test';
import assert from 'node:assert';
import { analyzeJobFit } from '../src/services/api.js';

test('analyzeJobFit sends correct fields and returns structured data', async () => {
  const originalFetch = globalThis.fetch;
  let capturedBody;

  globalThis.fetch = async (url, options) => {
    assert.strictEqual(url, 'http://127.0.0.1:8000/api/analyze');
    assert.strictEqual(options.method, 'POST');
    // Ensure Content-Type is NOT manually set (allows browser/fetch to set boundary)
    assert.strictEqual(options.headers, undefined);

    capturedBody = options.body;

    return {
      ok: true,
      status: 200,
      json: async () => ({
        ai_estimated_score: 85,
        summary: 'Solid full stack match.',
        matched_skills: [],
        missing_skills: [],
        tailoring_suggestions: [],
        interview_questions: [],
      }),
    };
  };

  try {
    const dummyFile = new Blob(['sample pdf content'], { type: 'application/pdf' });
    const result = await analyzeJobFit(dummyFile, 'Looking for an experienced Python developer.');

    assert.strictEqual(result.ai_estimated_score, 85);
    assert.strictEqual(result.summary, 'Solid full stack match.');
    assert.ok(capturedBody instanceof FormData);
    assert.ok(capturedBody.has('resume'));
    assert.ok(capturedBody.has('job_description'));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('analyzeJobFit handles HTTP error responses cleanly', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({
    ok: false,
    status: 400,
    statusText: 'Bad Request',
    json: async () => ({ detail: 'Job description is too short (minimum 50 characters required).' }),
  });

  try {
    const dummyFile = new Blob(['sample'], { type: 'application/pdf' });
    await assert.rejects(
      async () => {
        await analyzeJobFit(dummyFile, 'Short JD');
      },
      {
        message: 'Job description is too short (minimum 50 characters required).',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('analyzeJobFit handles server connection failure', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => {
    throw new TypeError('Failed to fetch');
  };

  try {
    const dummyFile = new Blob(['sample'], { type: 'application/pdf' });
    await assert.rejects(
      async () => {
        await analyzeJobFit(dummyFile, 'Some valid job description with enough characters.');
      },
      /Unable to connect to the backend server/
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
