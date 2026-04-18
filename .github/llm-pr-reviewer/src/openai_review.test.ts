/**
 * Tests for OpenAI Review module
 */

import { validateReviewResult, createFallbackResult, callOpenAIReview } from './openai_review';
import { ReviewResult } from './types';

// Mock OpenAI client factory
const createMockOpenAI = (responses: Array<{ output_text?: string; error?: Error }>) => {
  let callIndex = 0;
  return {
    responses: {
      create: jest.fn().mockImplementation(() => {
        const response = responses[callIndex++];
        if (response?.error) {
          return Promise.reject(response.error);
        }
        return Promise.resolve({ output_text: response?.output_text || '' });
      }),
    },
  } as any;
};

describe('validateReviewResult', () => {
  const validResult: ReviewResult = {
    summary: 'This PR adds a new feature',
    risk: {
      level: 'low',
      rationale: 'Simple change with good test coverage',
    },
    findings: [
      {
        severity: 'minor',
        title: 'Missing null check',
        detail: 'Consider adding a null check for the input parameter',
        file: 'src/utils.ts',
        ref: {
          type: 'line_range',
          start_line: 10,
          end_line: 15,
          hunk_header: null,
        },
      },
    ],
    tests: {
      add: ['Test for null input handling'],
      run: ['npm test'],
    },
    questions: ['Is this feature behind a flag?'],
    coverage_note: 'All files were reviewed',
  };

  it('should validate a correct review result', () => {
    const result = validateReviewResult(validResult);
    expect(result.valid).toBe(true);
    expect(result.errors).toBeUndefined();
  });

  it('should reject result with missing required fields', () => {
    const invalid = { summary: 'Test' };
    const result = validateReviewResult(invalid);

    expect(result.valid).toBe(false);
    expect(result.errors).toBeDefined();
    expect(result.errors).toContain('risk');
  });

  it('should reject result with invalid risk level', () => {
    const invalid = {
      ...validResult,
      risk: { level: 'critical', rationale: 'test' }, // 'critical' is not valid
    };
    const result = validateReviewResult(invalid);

    expect(result.valid).toBe(false);
    expect(result.errors).toBeDefined();
  });

  it('should reject result with invalid severity', () => {
    const invalid = {
      ...validResult,
      findings: [
        {
          severity: 'critical', // invalid
          title: 'Test',
          detail: 'Test',
          file: 'test.ts',
          ref: { type: 'unknown', start_line: null, end_line: null, hunk_header: null },
        },
      ],
    };
    const result = validateReviewResult(invalid);

    expect(result.valid).toBe(false);
    expect(result.errors).toBeDefined();
  });

  it('should reject result with extra properties', () => {
    const invalid = {
      ...validResult,
      extraField: 'should not be here',
    };
    const result = validateReviewResult(invalid);

    expect(result.valid).toBe(false);
    expect(result.errors).toBeDefined();
  });

  it('should accept result with all valid ref types', () => {
    const withDifferentRefs: ReviewResult = {
      ...validResult,
      findings: [
        {
          severity: 'blocker',
          title: 'Test 1',
          detail: 'Detail 1',
          file: 'file1.ts',
          ref: { type: 'line_range', start_line: 1, end_line: 5, hunk_header: null },
        },
        {
          severity: 'major',
          title: 'Test 2',
          detail: 'Detail 2',
          file: 'file2.ts',
          ref: { type: 'diff_hunk', start_line: null, end_line: null, hunk_header: '@@ -1,5 +1,10 @@' },
        },
        {
          severity: 'nit',
          title: 'Test 3',
          detail: 'Detail 3',
          file: 'file3.ts',
          ref: { type: 'unknown', start_line: null, end_line: null, hunk_header: null },
        },
      ],
    };
    const result = validateReviewResult(withDifferentRefs);

    expect(result.valid).toBe(true);
  });

  it('should accept empty arrays for findings, tests, and questions', () => {
    const minimal: ReviewResult = {
      summary: 'LGTM',
      risk: { level: 'low', rationale: 'No issues' },
      findings: [],
      tests: { add: [], run: [] },
      questions: [],
      coverage_note: '',
    };
    const result = validateReviewResult(minimal);

    expect(result.valid).toBe(true);
  });

  it('should reject non-object input', () => {
    expect(validateReviewResult('string')).toEqual(expect.objectContaining({ valid: false }));
    expect(validateReviewResult(123)).toEqual(expect.objectContaining({ valid: false }));
    expect(validateReviewResult(null)).toEqual(expect.objectContaining({ valid: false }));
    expect(validateReviewResult([])).toEqual(expect.objectContaining({ valid: false }));
  });
});

describe('createFallbackResult', () => {
  it('should create a fallback result with error message', () => {
    const result = createFallbackResult('API timeout');

    expect(result.summary).toContain('Unable to complete');
    expect(result.risk.level).toBe('medium');
    expect(result.findings).toEqual([]);
    expect(result.coverage_note).toContain('API timeout');
  });

  it('should include raw output note when provided', () => {
    const result = createFallbackResult('Parse error', '{"partial": "data"}');

    expect(result.coverage_note).toContain('Parse error');
    expect(result.coverage_note).toContain('Raw output was captured');
  });

  it('should create a valid result according to schema', () => {
    const result = createFallbackResult('Test error');
    const validation = validateReviewResult(result);

    expect(validation.valid).toBe(true);
  });
});

describe('callOpenAIReview - contract tests', () => {
  const validReviewJSON: ReviewResult = {
    summary: 'This PR adds user authentication',
    risk: { level: 'medium', rationale: 'Security-sensitive changes' },
    findings: [
      {
        severity: 'minor',
        title: 'Consider rate limiting',
        detail: 'Add rate limiting to login endpoint',
        file: 'src/auth.ts',
        ref: { type: 'line_range', start_line: 42, end_line: 50, hunk_header: null },
      },
    ],
    tests: { add: ['Test for failed login attempts'], run: ['npm test'] },
    questions: ['Will this work with SSO?'],
    coverage_note: 'All authentication files reviewed',
  };

  const prContent = '# PR Title: Add authentication\n\n## Description\nAdds login flow';
  const options = { model: 'gpt-5.2', effort: 'high' as const };

  it('should return valid result when OpenAI returns valid JSON', async () => {
    const mockClient = createMockOpenAI([
      { output_text: JSON.stringify(validReviewJSON) },
    ]);

    const result = await callOpenAIReview(mockClient, prContent, options);

    expect(result.result).toEqual(validReviewJSON);
    expect(result.error).toBeUndefined();
    expect(mockClient.responses.create).toHaveBeenCalledTimes(1);
  });

  it('should retry with schema repair on invalid JSON and succeed', async () => {
    const mockClient = createMockOpenAI([
      { output_text: 'invalid json {' }, // First call returns invalid JSON
      { output_text: JSON.stringify(validReviewJSON) }, // Retry succeeds
    ]);

    const result = await callOpenAIReview(mockClient, prContent, options);

    expect(result.result).toEqual(validReviewJSON);
    expect(result.error).toBeUndefined();
    expect(mockClient.responses.create).toHaveBeenCalledTimes(2);
  });

  it('should retry on schema validation failure and succeed', async () => {
    const invalidSchemaResult = { ...validReviewJSON, risk: { level: 'critical', rationale: 'test' } };
    const mockClient = createMockOpenAI([
      { output_text: JSON.stringify(invalidSchemaResult) }, // First call returns invalid schema
      { output_text: JSON.stringify(validReviewJSON) }, // Retry succeeds
    ]);

    const result = await callOpenAIReview(mockClient, prContent, options);

    expect(result.result).toEqual(validReviewJSON);
    expect(result.error).toBeUndefined();
    expect(mockClient.responses.create).toHaveBeenCalledTimes(2);
  });

  it('should return error when retry also fails with invalid JSON', async () => {
    const mockClient = createMockOpenAI([
      { output_text: 'invalid json' },
      { output_text: 'still invalid json' },
    ]);

    const result = await callOpenAIReview(mockClient, prContent, options);

    expect(result.result).toBeNull();
    expect(result.error).toContain('Failed to parse JSON');
    expect(mockClient.responses.create).toHaveBeenCalledTimes(2);
  });

  it('should return error when retry also fails with invalid schema', async () => {
    const invalidSchemaResult = { summary: 'only summary' }; // Missing required fields
    const mockClient = createMockOpenAI([
      { output_text: JSON.stringify(invalidSchemaResult) },
      { output_text: JSON.stringify(invalidSchemaResult) },
    ]);

    const result = await callOpenAIReview(mockClient, prContent, options);

    expect(result.result).toBeNull();
    expect(result.error).toContain('Schema validation failed');
    expect(mockClient.responses.create).toHaveBeenCalledTimes(2);
  });

  it('should return error when API call throws', async () => {
    const mockClient = createMockOpenAI([
      { error: new Error('API rate limit exceeded') },
    ]);

    const result = await callOpenAIReview(mockClient, prContent, options);

    expect(result.result).toBeNull();
    expect(result.error).toContain('API rate limit exceeded');
    expect(mockClient.responses.create).toHaveBeenCalledTimes(1);
  });

  it('should return error when retry API call throws', async () => {
    const mockClient = createMockOpenAI([
      { output_text: 'invalid json' },
      { error: new Error('Network error during retry') },
    ]);

    const result = await callOpenAIReview(mockClient, prContent, options);

    expect(result.result).toBeNull();
    expect(result.error).toContain('Retry failed');
    expect(result.error).toContain('Network error during retry');
    expect(mockClient.responses.create).toHaveBeenCalledTimes(2);
  });

  it('should include raw output in response for debugging', async () => {
    const rawOutput = JSON.stringify(validReviewJSON);
    const mockClient = createMockOpenAI([{ output_text: rawOutput }]);

    const result = await callOpenAIReview(mockClient, prContent, options);

    expect(result.rawOutput).toBe(rawOutput);
  });

  it('should handle xhigh effort level by mapping to high', async () => {
    const mockClient = createMockOpenAI([
      { output_text: JSON.stringify(validReviewJSON) },
    ]);

    const xhighOptions = { model: 'gpt-5.2', effort: 'xhigh' as const };
    const result = await callOpenAIReview(mockClient, prContent, xhighOptions);

    expect(result.result).toEqual(validReviewJSON);
    // Verify API was called with 'high' (not 'xhigh')
    const callArgs = mockClient.responses.create.mock.calls[0][0];
    expect(callArgs.reasoning.effort).toBe('high');
  });
});
