/**
 * Tests for PR Packet module
 */

import { truncatePatch, formatPRPacketForPrompt, isPRLarge, buildPRPacket, isTestPath } from './pr_packet';
import { PRPacket, ChangedFile } from './types';

// Mock Octokit for pagination tests
const createMockOctokit = (options: {
  prData?: { title: string; body: string | null };
  filesData?: Array<{ filename: string; status: string; additions: number; deletions: number; patch?: string }>;
  paginateFiles?: boolean;
}) => {
  const { prData, filesData, paginateFiles } = options;

  const mockPaginate = jest.fn().mockImplementation(async (method: any, params: any) => {
    // Return all files data for pagination
    return filesData || [];
  });

  return {
    pulls: {
      get: jest.fn().mockResolvedValue({
        data: prData || { title: 'Test PR', body: 'Description' },
      }),
      listFiles: jest.fn().mockResolvedValue({
        data: paginateFiles ? [] : (filesData || []),
      }),
    },
    paginate: mockPaginate,
  } as any;
};

describe('truncatePatch', () => {
  it('should not truncate patches within size limit', () => {
    const patch = 'line1\nline2\nline3';
    const result = truncatePatch(patch, 100);

    expect(result.truncated).toBe(false);
    expect(result.patch).toBe(patch);
  });

  it('should truncate patches exceeding size limit', () => {
    const patch = 'a'.repeat(1000);
    const result = truncatePatch(patch, 100);

    expect(result.truncated).toBe(true);
    expect(result.patch.length).toBeLessThan(1000);
    expect(result.patch).toContain('[... PATCH TRUNCATED');
  });

  it('should truncate at line boundary when possible', () => {
    const patch = 'line1\nline2\nline3\nline4\nline5';
    const result = truncatePatch(patch, 15);

    expect(result.truncated).toBe(true);
    // Should truncate at a newline boundary
    expect(result.patch).toContain('line1');
  });

  it('should be deterministic with same input', () => {
    const patch = 'a'.repeat(500) + '\n' + 'b'.repeat(500);
    const result1 = truncatePatch(patch, 200);
    const result2 = truncatePatch(patch, 200);

    expect(result1.patch).toBe(result2.patch);
    expect(result1.truncated).toBe(result2.truncated);
  });
});

describe('formatPRPacketForPrompt', () => {
  const createMockPacket = (overrides?: Partial<PRPacket>): PRPacket => ({
    title: 'Test PR',
    body: 'This is a test PR description',
    files: [
      {
        filename: 'src/test.ts',
        status: 'modified',
        additions: 10,
        deletions: 5,
        patch: '@@ -1,5 +1,10 @@\n+new line',
      },
    ],
    totalAdditions: 10,
    totalDeletions: 5,
    truncated: false,
    ...overrides,
  });

  it('should format a basic PR packet', () => {
    const packet = createMockPacket();
    const result = formatPRPacketForPrompt(packet);

    expect(result).toContain('# PR Title: Test PR');
    expect(result).toContain('This is a test PR description');
    expect(result).toContain('10 additions');
    expect(result).toContain('5 deletions');
    expect(result).toContain('src/test.ts');
    expect(result).toContain('@@ -1,5 +1,10 @@');
  });

  it('should include truncation notes when packet is truncated', () => {
    const packet = createMockPacket({
      truncated: true,
      truncationNote: 'large-file.bin: no patch available',
    });
    const result = formatPRPacketForPrompt(packet);

    expect(result).toContain('## Coverage Limitations');
    expect(result).toContain('large-file.bin: no patch available');
  });

  it('should handle missing PR body', () => {
    const packet = createMockPacket({ body: '' });
    const result = formatPRPacketForPrompt(packet);

    expect(result).toContain('(No description provided)');
  });

  it('should handle files without patches', () => {
    const packet = createMockPacket({
      files: [
        {
          filename: 'binary.bin',
          status: 'added',
          additions: 0,
          deletions: 0,
          truncated: true,
        },
      ],
    });
    const result = formatPRPacketForPrompt(packet);

    expect(result).toContain('binary.bin');
    expect(result).toContain('(Patch not available or omitted due to size)');
  });

  it('should format multiple files', () => {
    const packet = createMockPacket({
      files: [
        {
          filename: 'file1.ts',
          status: 'added',
          additions: 20,
          deletions: 0,
          patch: '+new content',
        },
        {
          filename: 'file2.ts',
          status: 'deleted',
          additions: 0,
          deletions: 15,
          patch: '-removed content',
        },
      ],
      totalAdditions: 20,
      totalDeletions: 15,
    });
    const result = formatPRPacketForPrompt(packet);

    expect(result).toContain('file1.ts');
    expect(result).toContain('file2.ts');
    expect(result).toContain('+new content');
    expect(result).toContain('-removed content');
  });
});

describe('isPRLarge', () => {
  it('should return false for small PRs', () => {
    const packet: PRPacket = {
      title: 'Small PR',
      body: '',
      files: Array(5).fill({
        filename: 'test.ts',
        status: 'modified',
        additions: 10,
        deletions: 5,
      }),
      totalAdditions: 50,
      totalDeletions: 25,
      truncated: false,
    };

    expect(isPRLarge(packet)).toBe(false);
  });

  it('should return true for PRs with many changes', () => {
    const packet: PRPacket = {
      title: 'Large PR',
      body: '',
      files: [],
      totalAdditions: 400,
      totalDeletions: 200,
      truncated: false,
    };

    expect(isPRLarge(packet)).toBe(true);
  });

  it('should return true for PRs with many files', () => {
    const packet: PRPacket = {
      title: 'Many files PR',
      body: '',
      files: Array(25).fill({
        filename: 'test.ts',
        status: 'modified',
        additions: 1,
        deletions: 1,
      }),
      totalAdditions: 25,
      totalDeletions: 25,
      truncated: false,
    };

    expect(isPRLarge(packet)).toBe(true);
  });
});

describe('buildPRPacket - pagination', () => {
  it('should use octokit.paginate to fetch all files', async () => {
    // Create 150 mock files (more than 100, the per_page limit)
    const manyFiles = Array.from({ length: 150 }, (_, i) => ({
      filename: `file${i}.ts`,
      status: 'modified',
      additions: 1,
      deletions: 1,
      patch: `+line${i}`,
    }));

    const mockOctokit = createMockOctokit({
      filesData: manyFiles,
      paginateFiles: true,
    });

    const packet = await buildPRPacket(mockOctokit, {
      owner: 'test',
      repo: 'repo',
      prNumber: 1,
    });

    // Should have called paginate
    expect(mockOctokit.paginate).toHaveBeenCalled();
    // Should have all 150 files
    expect(packet.files.length).toBe(150);
  });

  it('should add truncation note when hitting GitHub API file limit', async () => {
    // Create exactly 3000 files (GitHub's limit)
    const maxFiles = Array.from({ length: 3000 }, (_, i) => ({
      filename: `file${i}.ts`,
      status: 'modified',
      additions: 1,
      deletions: 1,
      patch: `+line${i}`,
    }));

    const mockOctokit = createMockOctokit({
      filesData: maxFiles,
      paginateFiles: true,
    });

    const packet = await buildPRPacket(mockOctokit, {
      owner: 'test',
      repo: 'repo',
      prNumber: 1,
    });

    expect(packet.truncated).toBe(true);
    expect(packet.truncationNote).toContain('GitHub API limit');
  });
});

describe('buildPRPacket - sensitive file handling', () => {
  it('should exclude .env files', async () => {
    const mockOctokit = createMockOctokit({
      filesData: [
        { filename: 'src/app.ts', status: 'modified', additions: 10, deletions: 5, patch: '+code' },
        { filename: '.env', status: 'modified', additions: 1, deletions: 0, patch: '+SECRET=xxx' },
        { filename: '.env.local', status: 'added', additions: 2, deletions: 0, patch: '+API_KEY=yyy' },
      ],
      paginateFiles: true,
    });

    const packet = await buildPRPacket(mockOctokit, {
      owner: 'test',
      repo: 'repo',
      prNumber: 1,
    });

    // Should have truncation notes for sensitive files
    expect(packet.truncated).toBe(true);
    expect(packet.truncationNote).toContain('excluded (sensitive file pattern)');

    // .env files should not have patches
    const envFile = packet.files.find(f => f.filename === '.env');
    expect(envFile?.patch).toBeUndefined();
    expect(envFile?.truncated).toBe(true);
  });

  it('should exclude files in secrets directories', async () => {
    const mockOctokit = createMockOctokit({
      filesData: [
        { filename: 'src/app.ts', status: 'modified', additions: 10, deletions: 5, patch: '+code' },
        { filename: 'config/secrets/api.json', status: 'modified', additions: 1, deletions: 0, patch: '+{"key":"xxx"}' },
      ],
      paginateFiles: true,
    });

    const packet = await buildPRPacket(mockOctokit, {
      owner: 'test',
      repo: 'repo',
      prNumber: 1,
    });

    expect(packet.truncated).toBe(true);
    const secretFile = packet.files.find(f => f.filename.includes('secrets'));
    expect(secretFile?.patch).toBeUndefined();
  });

  it('should redact potential secrets from patches', async () => {
    const mockOctokit = createMockOctokit({
      filesData: [
        {
          filename: 'src/config.ts',
          status: 'modified',
          additions: 1,
          deletions: 0,
          // Contains a pattern that looks like an API key
          patch: '+const apiKey = "sk-abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn";',
        },
      ],
      paginateFiles: true,
    });

    const packet = await buildPRPacket(mockOctokit, {
      owner: 'test',
      repo: 'repo',
      prNumber: 1,
    });

    // The patch should have [REDACTED] instead of the key
    const configFile = packet.files.find(f => f.filename === 'src/config.ts');
    expect(configFile?.patch).toContain('[REDACTED]');
    expect(configFile?.patch).not.toContain('sk-abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn');
  });
});

describe('isTestPath', () => {
  describe('should match test files', () => {
    const testPaths = [
      // Directory-based patterns
      'test/foo.ts',
      'tests/foo.ts',
      'test/nested/bar.js',
      'tests/nested/bar.js',
      'src/__tests__/a.ts',
      'src/components/__tests__/Button.test.tsx',
      // File extension patterns (JS/TS)
      'a/b/foo.spec.tsx',
      'a/b/foo.test.jsx',
      'foo.test.ts',
      'foo.spec.js',
      'Component.test.tsx',
      'Component.spec.jsx',
      // Python patterns
      'pkg/test_bar.py',
      'pkg/bar_test.py',
      'pkg/conftest.py',
      'tests/conftest.py',
      'test_utils.py',
      'utils_test.py',
      // Edge cases - nested test directories
      'src/modules/test/helper.ts',
      'lib/tests/fixtures/data.json',
    ];

    test.each(testPaths)('%s', (path) => {
      expect(isTestPath(path)).toBe(true);
    });
  });

  describe('should NOT match non-test files', () => {
    const nonTestPaths = [
      // Words containing "test" but not test files
      'src/contest.py',
      'src/latest.ts',
      'src/mytestsHelper.ts', // "tests" in middle of word
      'src/testimony.ts',
      'src/attestation.js',
      'src/detest.ts',
      // Regular source files
      'src/components/Button.tsx',
      'lib/utils.py',
      'index.ts',
      'main.py',
      // Helper files that aren't tests
      'src/testing-utils.ts',
      'src/testHelpers.ts', // CamelCase, not a test
      // Documentation
      'docs/testing.md',
      'README.test.md', // .md not in test patterns
      // Edge cases - "test" in path but not test directory
      'src/latest/index.ts',
      'contest/main.py',
    ];

    test.each(nonTestPaths)('%s', (path) => {
      expect(isTestPath(path)).toBe(false);
    });
  });

  describe('should handle Windows-style paths', () => {
    const windowsPaths = [
      'test\\foo.ts',
      'tests\\nested\\bar.js',
      'src\\__tests__\\a.ts',
    ];

    test.each(windowsPaths)('%s', (path) => {
      expect(isTestPath(path)).toBe(true);
    });
  });
});

describe('buildPRPacket - test file handling', () => {
  it('should exclude test files and report count by default', async () => {
    const mockOctokit = createMockOctokit({
      filesData: [
        { filename: 'src/app.ts', status: 'modified', additions: 10, deletions: 5, patch: '+code' },
        { filename: 'tests/app.test.ts', status: 'modified', additions: 20, deletions: 10, patch: '+test code' },
        { filename: 'src/__tests__/util.spec.ts', status: 'added', additions: 15, deletions: 0, patch: '+more tests' },
      ],
      paginateFiles: true,
    });

    const packet = await buildPRPacket(mockOctokit, {
      owner: 'test',
      repo: 'repo',
      prNumber: 1,
    });

    expect(packet.truncated).toBe(true);
    expect(packet.truncationNote).toContain('2 test file(s) excluded from review');
    expect(packet.truncationNote).toContain('disable with skipTests: false');

    // Test files should not have patches
    const testFile = packet.files.find(f => f.filename === 'tests/app.test.ts');
    expect(testFile?.patch).toBeUndefined();
    expect(testFile?.truncated).toBe(true);

    // Non-test file should have patch
    const srcFile = packet.files.find(f => f.filename === 'src/app.ts');
    expect(srcFile?.patch).toBe('+code');
  });

  it('should include test files when skipTests is false', async () => {
    const mockOctokit = createMockOctokit({
      filesData: [
        { filename: 'src/app.ts', status: 'modified', additions: 10, deletions: 5, patch: '+code' },
        { filename: 'tests/app.test.ts', status: 'modified', additions: 20, deletions: 10, patch: '+test code' },
      ],
      paginateFiles: true,
    });

    const packet = await buildPRPacket(mockOctokit, {
      owner: 'test',
      repo: 'repo',
      prNumber: 1,
      config: { skipTests: false },
    });

    // Test files should have patches when skipTests is false
    const testFile = packet.files.find(f => f.filename === 'tests/app.test.ts');
    expect(testFile?.patch).toBe('+test code');
    expect(testFile?.truncated).toBeUndefined();

    // Should not mention test exclusion
    expect(packet.truncationNote || '').not.toContain('test file(s) excluded');
  });

  it('should order truncation notes correctly', async () => {
    const mockOctokit = createMockOctokit({
      filesData: [
        { filename: 'src/app.ts', status: 'modified', additions: 10, deletions: 5, patch: '+const key = "sk-abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn";' },
        { filename: '.env', status: 'modified', additions: 1, deletions: 0, patch: '+SECRET=xxx' },
        { filename: 'tests/app.test.ts', status: 'modified', additions: 20, deletions: 10, patch: '+test' },
      ],
      paginateFiles: true,
    });

    const packet = await buildPRPacket(mockOctokit, {
      owner: 'test',
      repo: 'repo',
      prNumber: 1,
    });

    // Check that notes are in the expected order: secrets, sensitive, tests, then details
    const notes = packet.truncationNote?.split('\n') || [];
    const secretsIndex = notes.findIndex(n => n.includes('secrets redacted'));
    const sensitiveIndex = notes.findIndex(n => n.includes('sensitive file(s)'));
    const testsIndex = notes.findIndex(n => n.includes('test file(s)'));
    const detailIndex = notes.findIndex(n => n.includes('.env: excluded'));

    expect(secretsIndex).toBeLessThan(sensitiveIndex);
    expect(sensitiveIndex).toBeLessThan(testsIndex);
    expect(testsIndex).toBeLessThan(detailIndex);
  });
});
