/**
 * Types and JSON schema for the LLM PR Reviewer
 */

// JSON Schema for OpenAI Structured Outputs (strict mode)
export const REVIEW_SCHEMA = {
  name: 'pr_review',
  strict: true,
  schema: {
    type: 'object',
    additionalProperties: false,
    required: ['summary', 'risk', 'findings', 'tests', 'questions', 'coverage_note'],
    properties: {
      summary: { type: 'string' },
      risk: {
        type: 'object',
        additionalProperties: false,
        required: ['level', 'rationale'],
        properties: {
          level: { type: 'string', enum: ['low', 'medium', 'high'] },
          rationale: { type: 'string' },
        },
      },
      findings: {
        type: 'array',
        items: {
          type: 'object',
          additionalProperties: false,
          required: ['severity', 'title', 'detail', 'file', 'ref'],
          properties: {
            severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] },
            title: { type: 'string' },
            detail: { type: 'string' },
            file: { type: 'string' },
            ref: {
              type: 'object',
              additionalProperties: false,
              required: ['type', 'start_line', 'end_line', 'hunk_header'],
              properties: {
                type: { type: 'string', enum: ['line_range', 'diff_hunk', 'unknown'] },
                start_line: { anyOf: [{ type: 'integer' }, { type: 'null' }] },
                end_line: { anyOf: [{ type: 'integer' }, { type: 'null' }] },
                hunk_header: { anyOf: [{ type: 'string' }, { type: 'null' }] },
              },
            },
          },
        },
      },
      tests: {
        type: 'object',
        additionalProperties: false,
        required: ['add', 'run'],
        properties: {
          add: { type: 'array', items: { type: 'string' } },
          run: { type: 'array', items: { type: 'string' } },
        },
      },
      questions: { type: 'array', items: { type: 'string' } },
      coverage_note: { type: 'string' },
    },
  },
} as const;

// TypeScript types matching the schema
export type RiskLevel = 'low' | 'medium' | 'high';
export type Severity = 'blocker' | 'major' | 'minor' | 'nit';
export type RefType = 'line_range' | 'diff_hunk' | 'unknown';

export interface FindingRef {
  type: RefType;
  start_line: number | null;
  end_line: number | null;
  hunk_header: string | null;
}

export interface Finding {
  severity: Severity;
  title: string;
  detail: string;
  file: string;
  ref: FindingRef;
}

export interface Risk {
  level: RiskLevel;
  rationale: string;
}

export interface Tests {
  add: string[];
  run: string[];
}

export interface ReviewResult {
  summary: string;
  risk: Risk;
  findings: Finding[];
  tests: Tests;
  questions: string[];
  coverage_note: string;
}

// PR Packet types
export interface ChangedFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  patch?: string;
  truncated?: boolean;
}

export interface PRPacket {
  title: string;
  body: string;
  files: ChangedFile[];
  totalAdditions: number;
  totalDeletions: number;
  truncated: boolean;
  truncationNote?: string;
}

// Configuration
export interface ReviewConfig {
  model: string;
  effort: 'low' | 'medium' | 'high' | 'xhigh';
  maxPacketSize: number;
  maxPatchSize: number;
  /**
   * Skip test files from review to save context window.
   * Set to false to include test file patches in review.
   * Default: true
   */
  skipTests: boolean;
}

export const DEFAULT_CONFIG: ReviewConfig = {
  model: 'gpt-5.2',
  effort: 'high',
  maxPacketSize: 250000, // ~250KB total packet size
  maxPatchSize: 25000, // ~25KB per file patch
  skipTests: true, // Exclude test files by default
};
