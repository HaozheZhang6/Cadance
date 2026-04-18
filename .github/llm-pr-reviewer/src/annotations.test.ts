/**
 * Tests for Annotations module
 */

import { emitAnnotations, emitSummaryAnnotation } from './annotations';
import { Finding } from './types';

describe('emitAnnotations', () => {
  let consoleSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleSpy = jest.spyOn(console, 'log').mockImplementation();
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  it('should not emit annotations for minor or nit findings', () => {
    const findings: Finding[] = [
      {
        severity: 'minor',
        title: 'Minor issue',
        detail: 'This is minor',
        file: 'test.ts',
        ref: { type: 'line_range', start_line: 1, end_line: null, hunk_header: null },
      },
      {
        severity: 'nit',
        title: 'Nit',
        detail: 'This is a nit',
        file: 'test.ts',
        ref: { type: 'unknown', start_line: null, end_line: null, hunk_header: null },
      },
    ];

    emitAnnotations(findings);

    expect(consoleSpy).not.toHaveBeenCalled();
  });

  it('should emit warning for blocker findings', () => {
    const findings: Finding[] = [
      {
        severity: 'blocker',
        title: 'Critical Issue',
        detail: 'This is critical',
        file: 'src/main.ts',
        ref: { type: 'line_range', start_line: 10, end_line: 15, hunk_header: null },
      },
    ];

    emitAnnotations(findings);

    expect(consoleSpy).toHaveBeenCalledTimes(1);
    const output = consoleSpy.mock.calls[0][0];
    expect(output).toContain('::warning');
    expect(output).toContain('file=src/main.ts');
    expect(output).toContain('line=10');
    expect(output).toContain('endLine=15');
    expect(output).toContain('title=LLM Review');
    expect(output).toContain('Critical Issue');
  });

  it('should emit warning for major findings', () => {
    const findings: Finding[] = [
      {
        severity: 'major',
        title: 'Major Issue',
        detail: 'This needs attention',
        file: 'api.ts',
        ref: { type: 'line_range', start_line: 42, end_line: null, hunk_header: null },
      },
    ];

    emitAnnotations(findings);

    expect(consoleSpy).toHaveBeenCalledTimes(1);
    const output = consoleSpy.mock.calls[0][0];
    expect(output).toContain('::warning');
    expect(output).toContain('file=api.ts');
    expect(output).toContain('line=42');
  });

  it('should emit annotation without line info when not available', () => {
    const findings: Finding[] = [
      {
        severity: 'blocker',
        title: 'Issue',
        detail: 'Details here',
        file: 'unknown.ts',
        ref: { type: 'unknown', start_line: null, end_line: null, hunk_header: null },
      },
    ];

    emitAnnotations(findings);

    expect(consoleSpy).toHaveBeenCalledTimes(1);
    const output = consoleSpy.mock.calls[0][0];
    expect(output).toContain('::warning');
    expect(output).toContain('file=unknown.ts');
    expect(output).not.toContain('line=');
  });

  it('should emit annotations for blocker/major even when file is empty or unknown', () => {
    const findings: Finding[] = [
      {
        severity: 'blocker',
        title: 'Issue',
        detail: 'Details',
        file: '',
        ref: { type: 'unknown', start_line: null, end_line: null, hunk_header: null },
      },
      {
        severity: 'major',
        title: 'Issue 2',
        detail: 'Details 2',
        file: 'unknown',
        ref: { type: 'unknown', start_line: null, end_line: null, hunk_header: null },
      },
    ];

    emitAnnotations(findings);

    // Annotations are emitted for blocker/major findings regardless of file info
    // GitHub will show them as general warnings without file references
    expect(consoleSpy).toHaveBeenCalledTimes(2);

    // Verify empty file doesn't include file parameter
    const call1 = consoleSpy.mock.calls[0][0];
    expect(call1).not.toContain('file=');

    // Verify 'unknown' file doesn't include file parameter (filtered out)
    const call2 = consoleSpy.mock.calls[1][0];
    expect(call2).not.toContain('file=');
  });

  it('should truncate long detail messages', () => {
    const longDetail = 'x'.repeat(300);
    const findings: Finding[] = [
      {
        severity: 'blocker',
        title: 'Issue',
        detail: longDetail,
        file: 'test.ts',
        ref: { type: 'line_range', start_line: 1, end_line: null, hunk_header: null },
      },
    ];

    emitAnnotations(findings);

    const output = consoleSpy.mock.calls[0][0];
    expect(output.length).toBeLessThan(longDetail.length + 100);
    expect(output).toContain('...');
  });

  it('should escape special characters in messages', () => {
    const findings: Finding[] = [
      {
        severity: 'blocker',
        title: 'Issue: with colon',
        detail: 'Line 1\nLine 2',
        file: 'test.ts',
        ref: { type: 'line_range', start_line: 1, end_line: null, hunk_header: null },
      },
    ];

    emitAnnotations(findings);

    const output = consoleSpy.mock.calls[0][0];
    // Newlines should be escaped
    expect(output).toContain('%0A');
    // Colons in the message should be escaped (but not in the command syntax)
    expect(output.match(/::/g)?.length).toBe(2); // Only command delimiters
  });

  it('should emit multiple annotations for multiple findings', () => {
    const findings: Finding[] = [
      {
        severity: 'blocker',
        title: 'Blocker 1',
        detail: 'Detail 1',
        file: 'a.ts',
        ref: { type: 'line_range', start_line: 1, end_line: null, hunk_header: null },
      },
      {
        severity: 'major',
        title: 'Major 1',
        detail: 'Detail 2',
        file: 'b.ts',
        ref: { type: 'line_range', start_line: 2, end_line: null, hunk_header: null },
      },
      {
        severity: 'blocker',
        title: 'Blocker 2',
        detail: 'Detail 3',
        file: 'c.ts',
        ref: { type: 'line_range', start_line: 3, end_line: null, hunk_header: null },
      },
    ];

    emitAnnotations(findings);

    expect(consoleSpy).toHaveBeenCalledTimes(3);
  });

  // Security tests for injection prevention
  describe('injection prevention', () => {
    it('should reject file paths containing newlines', () => {
      const warnSpy = jest.spyOn(console, 'warn').mockImplementation();
      const findings: Finding[] = [
        {
          severity: 'blocker',
          title: 'Issue',
          detail: 'Detail',
          file: 'src/test.ts\n::error::injected',
          ref: { type: 'line_range', start_line: 1, end_line: null, hunk_header: null },
        },
      ];

      emitAnnotations(findings);

      // Should emit annotation but WITHOUT the malicious file
      expect(consoleSpy).toHaveBeenCalledTimes(1);
      const output = consoleSpy.mock.calls[0][0];
      expect(output).not.toContain('file=');
      expect(output).not.toContain('::error');
      warnSpy.mockRestore();
    });

    it('should reject file paths containing colons that could inject commands', () => {
      const warnSpy = jest.spyOn(console, 'warn').mockImplementation();
      const findings: Finding[] = [
        {
          severity: 'blocker',
          title: 'Issue',
          detail: 'Detail',
          file: 'src/test.ts::error::injected',
          ref: { type: 'line_range', start_line: 1, end_line: null, hunk_header: null },
        },
      ];

      emitAnnotations(findings);

      // Should emit annotation but WITHOUT the malicious file
      expect(consoleSpy).toHaveBeenCalledTimes(1);
      const output = consoleSpy.mock.calls[0][0];
      expect(output).not.toContain('file=');
      warnSpy.mockRestore();
    });

    it('should reject file paths containing commas', () => {
      const warnSpy = jest.spyOn(console, 'warn').mockImplementation();
      const findings: Finding[] = [
        {
          severity: 'blocker',
          title: 'Issue',
          detail: 'Detail',
          file: 'src/test.ts,line=999',
          ref: { type: 'line_range', start_line: 1, end_line: null, hunk_header: null },
        },
      ];

      emitAnnotations(findings);

      // Should emit annotation but WITHOUT the malicious file
      expect(consoleSpy).toHaveBeenCalledTimes(1);
      const output = consoleSpy.mock.calls[0][0];
      expect(output).not.toContain('file=');
      warnSpy.mockRestore();
    });

    it('should accept valid file paths with slashes and dots', () => {
      const findings: Finding[] = [
        {
          severity: 'blocker',
          title: 'Issue',
          detail: 'Detail',
          file: 'src/components/Button.test.tsx',
          ref: { type: 'line_range', start_line: 1, end_line: null, hunk_header: null },
        },
      ];

      emitAnnotations(findings);

      expect(consoleSpy).toHaveBeenCalledTimes(1);
      const output = consoleSpy.mock.calls[0][0];
      expect(output).toContain('file=src/components/Button.test.tsx');
    });

    it('should accept file paths with @ symbol (scoped packages)', () => {
      const findings: Finding[] = [
        {
          severity: 'blocker',
          title: 'Issue',
          detail: 'Detail',
          file: 'node_modules/@types/node/index.d.ts',
          ref: { type: 'line_range', start_line: 1, end_line: null, hunk_header: null },
        },
      ];

      emitAnnotations(findings);

      expect(consoleSpy).toHaveBeenCalledTimes(1);
      const output = consoleSpy.mock.calls[0][0];
      expect(output).toContain('file=');
    });

    it('should clamp negative line numbers to 1', () => {
      const findings: Finding[] = [
        {
          severity: 'blocker',
          title: 'Issue',
          detail: 'Detail',
          file: 'test.ts',
          ref: { type: 'line_range', start_line: -5, end_line: null, hunk_header: null },
        },
      ];

      emitAnnotations(findings);

      expect(consoleSpy).toHaveBeenCalledTimes(1);
      const output = consoleSpy.mock.calls[0][0];
      expect(output).toContain('line=1');
    });

    it('should clamp excessively large line numbers', () => {
      const findings: Finding[] = [
        {
          severity: 'blocker',
          title: 'Issue',
          detail: 'Detail',
          file: 'test.ts',
          ref: { type: 'line_range', start_line: 999999999, end_line: null, hunk_header: null },
        },
      ];

      emitAnnotations(findings);

      expect(consoleSpy).toHaveBeenCalledTimes(1);
      const output = consoleSpy.mock.calls[0][0];
      expect(output).toContain('line=100000');
    });
  });
});

describe('emitSummaryAnnotation', () => {
  let consoleSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleSpy = jest.spyOn(console, 'log').mockImplementation();
  });

  afterEach(() => {
    consoleSpy.mockRestore();
  });

  it('should emit notice for low risk with no findings', () => {
    emitSummaryAnnotation('low', { blockers: 0, majors: 0, minors: 0, nits: 0 });

    const output = consoleSpy.mock.calls[0][0];
    expect(output).toContain('::notice');
    expect(output).toContain('No significant issues');
  });

  it('should emit warning for high risk', () => {
    emitSummaryAnnotation('high', { blockers: 0, majors: 1, minors: 0, nits: 0 });

    const output = consoleSpy.mock.calls[0][0];
    expect(output).toContain('::warning');
    expect(output).toContain('HIGH');
  });

  it('should emit warning when there are blockers', () => {
    emitSummaryAnnotation('low', { blockers: 1, majors: 0, minors: 0, nits: 0 });

    const output = consoleSpy.mock.calls[0][0];
    expect(output).toContain('::warning');
    expect(output).toContain('1 blocker');
  });

  it('should include all finding counts in message', () => {
    emitSummaryAnnotation('medium', { blockers: 2, majors: 3, minors: 4, nits: 5 });

    const output = consoleSpy.mock.calls[0][0];
    expect(output).toContain('2 blocker');
    expect(output).toContain('3 major');
    expect(output).toContain('4 minor');
    expect(output).toContain('5 nit');
  });

  it('should emit notice for medium risk with only minor/nit findings', () => {
    emitSummaryAnnotation('medium', { blockers: 0, majors: 0, minors: 2, nits: 3 });

    const output = consoleSpy.mock.calls[0][0];
    expect(output).toContain('::notice');
    expect(output).toContain('MEDIUM');
  });
});
