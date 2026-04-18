/**
 * PR Packet Builder
 * Fetches PR data from GitHub API and builds a packet for review.
 */

import { Octokit } from '@octokit/rest';
import { PRPacket, ChangedFile, ReviewConfig, DEFAULT_CONFIG } from './types';

/**
 * GitHub API limit for files per PR.
 */
const GITHUB_MAX_FILES = 3000;

/**
 * Path patterns to exclude from LLM review (sensitive files).
 * Uses simple glob-like matching.
 */
const SENSITIVE_PATH_PATTERNS = [
  /\.env($|\.)/i, // .env, .env.local, .env.production, etc.
  /\/secrets?\//i, // /secret/ or /secrets/
  /\/credentials?\//i, // /credential/ or /credentials/
  /\.pem$/i, // Private keys
  /\.key$/i, // Private keys
  /id_rsa/i, // SSH keys
  /id_ed25519/i, // SSH keys
  /\.p12$/i, // PKCS12 certificates
  /password/i, // Files with password in name
  /\.htpasswd$/i, // Apache password files
];

/**
 * Path patterns to exclude from LLM review (test files).
 * Tests can be large and fill context window without adding review value.
 */
const TEST_PATH_PATTERNS = [
  /^tests?\//i, // test/ or tests/ directory at root
  /\/tests?\//i, // /test/ or /tests/ directory anywhere
  /\/__tests__\//i, // __tests__/ (Jest convention)
  /\.test\.[jt]sx?$/i, // .test.js, .test.ts, .test.jsx, .test.tsx
  /\.spec\.[jt]sx?$/i, // .spec.js, .spec.ts, .spec.jsx, .spec.tsx
  /test_[^/]+\.py$/i, // test_*.py (pytest convention)
  /[^/]+_test\.py$/i, // *_test.py (pytest convention)
  /conftest\.py$/i, // pytest conftest files
];

/**
 * Common secret patterns to redact from patches.
 */
const SECRET_PATTERNS = [
  // API keys and tokens (generic patterns)
  /(?<=['"`:=\s])[A-Za-z0-9_-]{32,}(?=['"\s,\n])/g,
  // AWS access keys
  /AKIA[0-9A-Z]{16}/g,
  // GitHub tokens
  /gh[pousr]_[A-Za-z0-9_]{36,}/g,
  // OpenAI keys
  /sk-[A-Za-z0-9]{48,}/g,
  // Slack tokens
  /xox[baprs]-[A-Za-z0-9-]+/g,
  // Generic Bearer tokens in code
  /Bearer\s+[A-Za-z0-9._-]{20,}/gi,
];

/**
 * Redaction placeholder.
 */
const REDACTED = '[REDACTED]';

export interface PRPacketOptions {
  owner: string;
  repo: string;
  prNumber: number;
  config?: Partial<ReviewConfig>;
}

/**
 * Normalize path separators to forward slashes (POSIX style).
 * GitHub API uses forward slashes, but this ensures compatibility
 * if paths from other sources (e.g., local filesystem on Windows) are used.
 */
function normalizePath(filename: string): string {
  return filename.replace(/\\/g, '/');
}

/**
 * Check if a file path matches any sensitive pattern.
 */
function isSensitivePath(filename: string): boolean {
  const normalized = normalizePath(filename);
  return SENSITIVE_PATH_PATTERNS.some((pattern) => pattern.test(normalized));
}

/**
 * Check if a file path is a test file.
 */
export function isTestPath(filename: string): boolean {
  const normalized = normalizePath(filename);
  return TEST_PATH_PATTERNS.some((pattern) => pattern.test(normalized));
}

/**
 * Redact potential secrets from a patch.
 * Returns the redacted patch and whether any redaction occurred.
 */
function redactSecrets(patch: string): { patch: string; redacted: boolean } {
  let redacted = false;
  let result = patch;

  for (const pattern of SECRET_PATTERNS) {
    // Reset regex lastIndex for global patterns
    pattern.lastIndex = 0;
    if (pattern.test(result)) {
      redacted = true;
      pattern.lastIndex = 0;
      result = result.replace(pattern, REDACTED);
    }
  }

  return { patch: result, redacted };
}

/**
 * Truncate a patch to a maximum size with an explicit notice.
 */
export function truncatePatch(patch: string, maxSize: number): { patch: string; truncated: boolean } {
  if (patch.length <= maxSize) {
    return { patch, truncated: false };
  }

  // Find a good line boundary to truncate at
  const truncateAt = patch.lastIndexOf('\n', maxSize);
  const effectiveTruncateAt = truncateAt > maxSize * 0.8 ? truncateAt : maxSize;

  const truncatedPatch = patch.substring(0, effectiveTruncateAt);
  const truncationNotice = `\n\n[... PATCH TRUNCATED - ${patch.length - effectiveTruncateAt} bytes omitted ...]`;

  return {
    patch: truncatedPatch + truncationNotice,
    truncated: true,
  };
}

/**
 * Build a PR packet from GitHub API data.
 */
export async function buildPRPacket(
  octokit: Octokit,
  options: PRPacketOptions
): Promise<PRPacket> {
  const { owner, repo, prNumber } = options;
  const config = { ...DEFAULT_CONFIG, ...options.config };

  // Fetch PR details
  const { data: pr } = await octokit.pulls.get({
    owner,
    repo,
    pull_number: prNumber,
  });

  // Fetch all changed files with pagination
  const filesData = await octokit.paginate(octokit.pulls.listFiles, {
    owner,
    repo,
    pull_number: prNumber,
    per_page: 100,
  });

  let totalSize = 0;
  let packetTruncated = false;
  const truncationNotes: string[] = [];

  // Check if we hit GitHub's file limit
  if (filesData.length >= GITHUB_MAX_FILES) {
    truncationNotes.push(`GitHub API limit: only first ${GITHUB_MAX_FILES} files returned`);
    packetTruncated = true;
  }

  let sensitiveFilesSkipped = 0;
  let testFilesSkipped = 0;
  let secretsRedacted = false;

  const files: ChangedFile[] = filesData.map((file) => {
    const changedFile: ChangedFile = {
      filename: file.filename,
      status: file.status,
      additions: file.additions,
      deletions: file.deletions,
    };

    // Skip sensitive files entirely
    if (isSensitivePath(file.filename)) {
      sensitiveFilesSkipped++;
      changedFile.truncated = true;
      truncationNotes.push(`${file.filename}: excluded (sensitive file pattern)`);
      packetTruncated = true;
      return changedFile;
    }

    // Skip test files to save context window (configurable)
    if (config.skipTests && isTestPath(file.filename)) {
      testFilesSkipped++;
      changedFile.truncated = true;
      packetTruncated = true;
      return changedFile;
    }

    if (file.patch) {
      // Redact potential secrets from the patch
      const { patch: redactedPatch, redacted } = redactSecrets(file.patch);
      if (redacted) {
        secretsRedacted = true;
      }

      // Check if we need to truncate this patch
      if (redactedPatch.length > config.maxPatchSize) {
        const { patch, truncated } = truncatePatch(redactedPatch, config.maxPatchSize);
        changedFile.patch = patch;
        changedFile.truncated = truncated;
        if (truncated) {
          truncationNotes.push(`${file.filename}: patch truncated`);
          packetTruncated = true;
        }
      } else {
        changedFile.patch = redactedPatch;
      }
      totalSize += changedFile.patch?.length || 0;
    } else {
      // Patch missing (large diff or binary file)
      changedFile.truncated = true;
      truncationNotes.push(`${file.filename}: no patch available (binary or large file)`);
      packetTruncated = true;
    }

    return changedFile;
  });

  // Build summary notes in desired order (summary first, then details)
  const summaryNotes: string[] = [];
  if (secretsRedacted) {
    summaryNotes.push('Potential secrets redacted from patches');
  }
  if (sensitiveFilesSkipped > 0) {
    summaryNotes.push(`${sensitiveFilesSkipped} sensitive file(s) excluded from review`);
  }
  if (testFilesSkipped > 0) {
    const hint = config.skipTests ? ' (disable with skipTests: false)' : '';
    summaryNotes.push(`${testFilesSkipped} test file(s) excluded from review${hint}`);
  }
  // Prepend summary notes to detail notes
  truncationNotes.unshift(...summaryNotes);

  // Check if total packet exceeds max size
  const baseSize = (pr.title?.length || 0) + (pr.body?.length || 0);
  if (baseSize + totalSize > config.maxPacketSize) {
    // Sort files by importance (smaller patches first to include more files)
    files.sort((a, b) => (a.patch?.length || 0) - (b.patch?.length || 0));

    let currentSize = baseSize;
    for (const file of files) {
      const patchSize = file.patch?.length || 0;
      if (currentSize + patchSize > config.maxPacketSize && file.patch) {
        file.patch = undefined;
        file.truncated = true;
        truncationNotes.push(`${file.filename}: patch omitted due to size limits`);
        packetTruncated = true;
      } else {
        currentSize += patchSize;
      }
    }
  }

  return {
    title: pr.title,
    body: pr.body || '',
    files,
    totalAdditions: filesData.reduce((sum, f) => sum + f.additions, 0),
    totalDeletions: filesData.reduce((sum, f) => sum + f.deletions, 0),
    truncated: packetTruncated,
    truncationNote: truncationNotes.length > 0 ? truncationNotes.join('\n') : undefined,
  };
}

/**
 * Format a PR packet as text for the LLM prompt.
 */
export function formatPRPacketForPrompt(packet: PRPacket): string {
  const lines: string[] = [];

  lines.push(`# PR Title: ${packet.title}`);
  lines.push('');
  lines.push('## PR Description');
  lines.push(packet.body || '(No description provided)');
  lines.push('');
  lines.push(`## Summary: ${packet.totalAdditions} additions, ${packet.totalDeletions} deletions across ${packet.files.length} files`);
  lines.push('');

  if (packet.truncated && packet.truncationNote) {
    lines.push('## Coverage Limitations');
    lines.push(packet.truncationNote);
    lines.push('');
  }

  lines.push('## Changed Files');
  for (const file of packet.files) {
    lines.push(`### ${file.filename} (${file.status}, +${file.additions}/-${file.deletions})`);
    if (file.patch) {
      lines.push('```diff');
      lines.push(file.patch);
      lines.push('```');
    } else if (file.truncated) {
      lines.push('(Patch not available or omitted due to size)');
    }
    lines.push('');
  }

  return lines.join('\n');
}

/**
 * Determine if a PR is "large" and should use higher reasoning effort.
 */
export function isPRLarge(packet: PRPacket): boolean {
  const totalChanges = packet.totalAdditions + packet.totalDeletions;
  return totalChanges > 500 || packet.files.length > 20;
}
