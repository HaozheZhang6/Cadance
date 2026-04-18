/**
 * Tests for Render module
 */

import { renderReviewMarkdown, renderFallbackMarkdown, COMMENT_MARKER } from './render';
import { ReviewResult } from './types';

describe('renderReviewMarkdown', () => {
  const baseResult: ReviewResult = {
    summary: 'This PR implements a new authentication flow',
    risk: {
      level: 'medium',
      rationale: 'Security-sensitive changes require careful review',
    },
    findings: [],
    tests: { add: [], run: [] },
    questions: [],
    coverage_note: 'All files were reviewed',
  };

  it('should include the comment marker', () => {
    const markdown = renderReviewMarkdown(baseResult);
    expect(markdown).toContain(COMMENT_MARKER);
  });

  it('should include the header', () => {
    const markdown = renderReviewMarkdown(baseResult);
    expect(markdown).toContain('# :robot: LLM PR Review');
  });

  it('should include commit SHA when provided', () => {
    const markdown = renderReviewMarkdown(baseResult, 'abc1234567890');
    expect(markdown).toContain('abc1234');
  });

  it('should include summary section', () => {
    const markdown = renderReviewMarkdown(baseResult);
    expect(markdown).toContain('## Summary');
    expect(markdown).toContain('new authentication flow');
  });

  it('should include risk assessment with correct emoji', () => {
    const lowRisk = renderReviewMarkdown({ ...baseResult, risk: { level: 'low', rationale: 'Safe' } });
    expect(lowRisk).toContain(':white_check_mark:');

    const mediumRisk = renderReviewMarkdown(baseResult);
    expect(mediumRisk).toContain(':yellow_circle:');

    const highRisk = renderReviewMarkdown({ ...baseResult, risk: { level: 'high', rationale: 'Risky' } });
    expect(highRisk).toContain(':red_circle:');
  });

  it('should show no issues found when findings are empty', () => {
    const markdown = renderReviewMarkdown(baseResult);
    expect(markdown).toContain('No significant issues found');
  });

  it('should render findings with correct severity formatting', () => {
    const withFindings: ReviewResult = {
      ...baseResult,
      findings: [
        {
          severity: 'blocker',
          title: 'SQL Injection vulnerability',
          detail: 'User input is not sanitized',
          file: 'src/db.ts',
          ref: { type: 'line_range', start_line: 42, end_line: 45, hunk_header: null },
        },
        {
          severity: 'major',
          title: 'Missing error handling',
          detail: 'Async function lacks try-catch',
          file: 'src/api.ts',
          ref: { type: 'diff_hunk', start_line: null, end_line: null, hunk_header: '@@ -10,5 +10,10 @@' },
        },
        {
          severity: 'minor',
          title: 'Unused import',
          detail: 'lodash is imported but not used',
          file: 'src/utils.ts',
          ref: { type: 'line_range', start_line: 1, end_line: null, hunk_header: null },
        },
        {
          severity: 'nit',
          title: 'Consider renaming variable',
          detail: 'x is not descriptive',
          file: 'src/calc.ts',
          ref: { type: 'unknown', start_line: null, end_line: null, hunk_header: null },
        },
      ],
    };

    const markdown = renderReviewMarkdown(withFindings);

    // Check severity emojis
    expect(markdown).toContain(':no_entry:');
    expect(markdown).toContain(':warning:');
    expect(markdown).toContain(':information_source:');
    expect(markdown).toContain(':bulb:');

    // Check finding counts
    expect(markdown).toContain('1 blocker(s)');
    expect(markdown).toContain('1 major');
    expect(markdown).toContain('1 minor');
    expect(markdown).toContain('1 nit(s)');

    // Check file references
    expect(markdown).toContain('src/db.ts:42-45');
    expect(markdown).toContain('src/api.ts (@@ -10,5 +10,10 @@)');
    expect(markdown).toContain('src/utils.ts:1');
    expect(markdown).toContain('src/calc.ts');
  });

  it('should render tests section when tests are provided', () => {
    const withTests: ReviewResult = {
      ...baseResult,
      tests: {
        add: ['Test for empty input', 'Integration test for auth flow'],
        run: ['npm test', 'npm run e2e'],
      },
    };

    const markdown = renderReviewMarkdown(withTests);

    expect(markdown).toContain('## Recommended Tests');
    expect(markdown).toContain('Test for empty input');
    expect(markdown).toContain('Integration test for auth flow');
    expect(markdown).toContain('npm test');
    expect(markdown).toContain('npm run e2e');
  });

  it('should render questions section when questions are provided', () => {
    const withQuestions: ReviewResult = {
      ...baseResult,
      questions: [
        'Is this feature behind a flag?',
        'Has this been tested on staging?',
      ],
    };

    const markdown = renderReviewMarkdown(withQuestions);

    expect(markdown).toContain('## Questions for Author');
    expect(markdown).toContain('1. Is this feature behind a flag?');
    expect(markdown).toContain('2. Has this been tested on staging?');
  });

  it('should render coverage note in collapsible section', () => {
    const markdown = renderReviewMarkdown(baseResult);

    expect(markdown).toContain('<details>');
    expect(markdown).toContain('<summary>Coverage Note</summary>');
    expect(markdown).toContain('All files were reviewed');
    expect(markdown).toContain('</details>');
  });

  it('should include advisory disclaimer', () => {
    const markdown = renderReviewMarkdown(baseResult);
    expect(markdown).toContain('advisory only');
  });
});

describe('renderFallbackMarkdown', () => {
  it('should include the comment marker', () => {
    const markdown = renderFallbackMarkdown('Test error');
    expect(markdown).toContain(COMMENT_MARKER);
  });

  it('should show error message', () => {
    const markdown = renderFallbackMarkdown('API rate limit exceeded');
    expect(markdown).toContain('Review could not be completed');
    expect(markdown).toContain('API rate limit exceeded');
  });

  it('should include commit SHA when provided', () => {
    const markdown = renderFallbackMarkdown('Error', 'abc123456');
    expect(markdown).toContain('abc1234');
  });

  it('should not include raw output section (raw output is logged to Actions, not PR comments)', () => {
    const markdown = renderFallbackMarkdown('Simple error');
    expect(markdown).not.toContain('Raw LLM Output');
    expect(markdown).not.toContain('<details>');
  });

  it('should encourage manual review', () => {
    const markdown = renderFallbackMarkdown('Error');
    expect(markdown).toContain('manual review');
  });
});

describe('Markdown snapshot tests', () => {
  it('should produce consistent output for standard review', () => {
    const result: ReviewResult = {
      summary: 'Adds user profile editing capability',
      risk: { level: 'low', rationale: 'Standard CRUD operations' },
      findings: [
        {
          severity: 'minor',
          title: 'Consider input validation',
          detail: 'Email field should be validated before save',
          file: 'src/profile.ts',
          ref: { type: 'line_range', start_line: 25, end_line: null, hunk_header: null },
        },
      ],
      tests: { add: ['Validate email format test'], run: ['npm test'] },
      questions: [],
      coverage_note: 'All 3 files reviewed',
    };

    const markdown = renderReviewMarkdown(result, 'deadbeef123');

    // Verify key structural elements are present and in order
    const sections = [
      COMMENT_MARKER,
      '# :robot: LLM PR Review',
      '## Summary',
      '## Risk Assessment',
      '## Findings',
      '## Recommended Tests',
      '<details>',
      '</details>',
      '---',
    ];

    let lastIndex = -1;
    for (const section of sections) {
      const index = markdown.indexOf(section);
      expect(index).toBeGreaterThan(lastIndex);
      lastIndex = index;
    }
  });
});
