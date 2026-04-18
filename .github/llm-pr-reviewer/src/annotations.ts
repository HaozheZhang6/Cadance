/**
 * Annotations Module
 * Emits GitHub Actions workflow annotations for findings.
 */

import { Finding, Severity } from './types';

/**
 * Safe file path pattern - only allows word chars, dots, slashes, hyphens.
 * This prevents injection of special characters that could break workflow commands.
 */
const SAFE_PATH_PATTERN = /^[\w./@-]+$/;

/**
 * Maximum reasonable line number to prevent abuse.
 */
const MAX_LINE_NUMBER = 100000;

/**
 * Escape a string for use in workflow commands.
 * GitHub Actions workflow commands use special characters.
 */
function escapeAnnotationMessage(message: string): string {
  return message
    .replace(/%/g, '%25')
    .replace(/\r/g, '%0D')
    .replace(/\n/g, '%0A')
    .replace(/:/g, '%3A')
    .replace(/,/g, '%2C');
}

/**
 * Validate and sanitize a file path for use in annotations.
 * Returns undefined if the path is invalid or potentially malicious.
 */
function sanitizeFilePath(file: string): string | undefined {
  // Reject empty or obviously invalid paths
  if (!file || file === '' || file === 'unknown') {
    return undefined;
  }

  // Check against safe path pattern to prevent injection
  if (!SAFE_PATH_PATTERN.test(file)) {
    console.warn(`Annotation: Rejected unsafe file path: ${file.substring(0, 50)}`);
    return undefined;
  }

  // Escape the path for workflow command safety
  return escapeAnnotationMessage(file);
}

/**
 * Clamp a line number to valid bounds.
 * Returns undefined if the line number is invalid.
 */
function clampLineNumber(line: number | null | undefined): number | undefined {
  if (line == null || !Number.isInteger(line)) {
    return undefined;
  }
  if (line < 1) {
    return 1;
  }
  if (line > MAX_LINE_NUMBER) {
    return MAX_LINE_NUMBER;
  }
  return line;
}

/**
 * Get the annotation level for a severity.
 */
function getAnnotationLevel(severity: Severity): 'error' | 'warning' | 'notice' {
  switch (severity) {
    case 'blocker':
      return 'warning'; // Use warning instead of error to keep advisory
    case 'major':
      return 'warning';
    case 'minor':
      return 'notice';
    case 'nit':
      return 'notice';
    default:
      return 'notice';
  }
}

/**
 * Build an annotation command string.
 * Note: file parameter should already be sanitized/escaped before passing here.
 */
function buildAnnotationCommand(
  level: 'error' | 'warning' | 'notice',
  title: string,
  message: string,
  sanitizedFile?: string,
  startLine?: number,
  endLine?: number
): string {
  const params: string[] = [];

  // File is already sanitized and escaped by sanitizeFilePath()
  if (sanitizedFile) {
    params.push(`file=${sanitizedFile}`);
  }

  if (startLine !== undefined) {
    params.push(`line=${startLine}`);
  }

  if (endLine !== undefined && endLine !== startLine) {
    params.push(`endLine=${endLine}`);
  }

  params.push(`title=${escapeAnnotationMessage(title)}`);

  const paramsStr = params.join(',');
  const escapedMessage = escapeAnnotationMessage(message);

  return `::${level} ${paramsStr}::${escapedMessage}`;
}

/**
 * Emit annotations for findings.
 * Only emits annotations for blocker and major findings with known file/line info.
 */
export function emitAnnotations(findings: Finding[]): void {
  // Filter to only blocker and major findings
  const significantFindings = findings.filter(
    (f) => f.severity === 'blocker' || f.severity === 'major'
  );

  for (const finding of significantFindings) {
    const level = getAnnotationLevel(finding.severity);
    const title = `LLM Review: ${finding.title}`;

    // Truncate detail for annotation (keep it short)
    const shortDetail =
      finding.detail.length > 200
        ? finding.detail.substring(0, 197) + '...'
        : finding.detail;

    let sanitizedFile: string | undefined;
    let startLine: number | undefined;
    let endLine: number | undefined;

    // Extract and validate location info
    if (finding.file) {
      // Sanitize file path to prevent injection attacks
      sanitizedFile = sanitizeFilePath(finding.file);

      if (sanitizedFile && finding.ref.type === 'line_range') {
        // Clamp line numbers to valid bounds
        startLine = clampLineNumber(finding.ref.start_line);
        endLine = clampLineNumber(finding.ref.end_line);
      }
    }

    const command = buildAnnotationCommand(
      level,
      title,
      shortDetail,
      sanitizedFile,
      startLine,
      endLine
    );

    // Output the annotation command
    console.log(command);
  }
}

/**
 * Emit a summary annotation.
 */
export function emitSummaryAnnotation(
  riskLevel: string,
  findingCounts: { blockers: number; majors: number; minors: number; nits: number }
): void {
  const { blockers, majors, minors, nits } = findingCounts;
  const total = blockers + majors + minors + nits;

  if (total === 0 && riskLevel === 'low') {
    console.log('::notice title=LLM PR Review::No significant issues found.');
    return;
  }

  const parts: string[] = [];
  if (blockers > 0) parts.push(`${blockers} blocker(s)`);
  if (majors > 0) parts.push(`${majors} major`);
  if (minors > 0) parts.push(`${minors} minor`);
  if (nits > 0) parts.push(`${nits} nit(s)`);

  const message = `Risk: ${riskLevel.toUpperCase()}. Found: ${parts.join(', ') || 'none'}`;

  const level = riskLevel === 'high' || blockers > 0 ? 'warning' : 'notice';
  console.log(`::${level} title=LLM PR Review Summary::${escapeAnnotationMessage(message)}`);
}
