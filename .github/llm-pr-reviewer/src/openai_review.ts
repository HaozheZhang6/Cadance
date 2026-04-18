/**
 * OpenAI Review Module
 * Calls OpenAI API with structured outputs to review PRs.
 */

import OpenAI from 'openai';
import Ajv from 'ajv';
import { ReviewResult, REVIEW_SCHEMA } from './types';

const SYSTEM_PROMPT = `You are PRReviewGPT, a senior engineer and security reviewer. You will be given PR title/body, changed file list, and diffs/patches (and sometimes file contents). Your job:
1) Summarize the change.
2) Identify risks: correctness, security, privacy, reliability, performance, maintainability, backwards compatibility.
3) Provide actionable findings referencing file + line range when possible; otherwise reference diff hunk.
4) Recommend tests to add and commands to run only if derivable.

Hard rules:
- Do not invent repo context.
- Do not claim you executed code/tests.
- Focus on material issues.
- Be explicit about uncertainty and coverage limits.
- Return ONLY JSON matching the schema.

Exceptions (DO NOT flag these as issues):
- Workflow files using pull_request vs pull_request_target triggers: The workflow configuration for this repository's LLM PR reviewer is intentionally designed and will use pull_request_target with base branch checkout. Do not flag secret exposure related to workflow triggers.`;

const SCHEMA_REPAIR_INSTRUCTION = `Your previous response did not match the required JSON schema. Please ensure your response is valid JSON that exactly matches this schema:
- Required fields: summary (string), risk (object with level and rationale), findings (array), tests (object with add and run arrays), questions (array), coverage_note (string)
- risk.level must be one of: "low", "medium", "high"
- Each finding must have: severity (blocker/major/minor/nit), title, detail, file, ref (object with type, start_line, end_line, hunk_header)
- ref.type must be one of: "line_range", "diff_hunk", "unknown"
- ref.start_line, ref.end_line must be integers or null
- ref.hunk_header must be a string or null`;

export interface ReviewOptions {
  model: string;
  effort: 'low' | 'medium' | 'high' | 'xhigh';
}

// Map internal effort levels to OpenAI SDK-compatible values
// OpenAI SDK only supports 'low' | 'medium' | 'high', so 'xhigh' is mapped to 'high'
type OpenAIEffort = 'low' | 'medium' | 'high';
function mapEffortToOpenAI(effort: ReviewOptions['effort']): OpenAIEffort {
  return effort === 'xhigh' ? 'high' : effort;
}

// AJV schema for validation (same structure but in JSON Schema draft-07 format)
const ajvSchema = {
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
              start_line: { type: ['integer', 'null'] },
              end_line: { type: ['integer', 'null'] },
              hunk_header: { type: ['string', 'null'] },
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
};

const ajv = new Ajv({ strict: true, allErrors: true });
const validateSchema = ajv.compile(ajvSchema);

/**
 * Validate a review result against the schema.
 */
export function validateReviewResult(data: unknown): { valid: boolean; errors?: string } {
  const valid = validateSchema(data);
  if (!valid) {
    const errors = validateSchema.errors
      ?.map((e) => `${e.instancePath} ${e.message}`)
      .join('; ');
    return { valid: false, errors };
  }
  return { valid: true };
}

/**
 * Call OpenAI to review a PR.
 */
export async function callOpenAIReview(
  client: OpenAI,
  prContent: string,
  options: ReviewOptions
): Promise<{ result: ReviewResult | null; rawOutput: string; error?: string }> {
  const { model, effort } = options;
  const apiEffort = mapEffortToOpenAI(effort);

  try {
    // First attempt with structured outputs
    const response = await client.responses.create({
      model,
      reasoning: { effort: apiEffort },
      input: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: prContent },
      ],
      text: {
        format: {
          type: 'json_schema',
          name: REVIEW_SCHEMA.name,
          schema: REVIEW_SCHEMA.schema,
          strict: true,
        },
      },
    });

    const rawOutput = response.output_text || '';

    // Parse and validate
    let parsed: unknown;
    try {
      parsed = JSON.parse(rawOutput);
    } catch {
      // Retry with schema repair instruction
      return await retryWithSchemaRepair(client, prContent, rawOutput, options);
    }

    const validation = validateReviewResult(parsed);
    if (!validation.valid) {
      // Retry with schema repair instruction
      return await retryWithSchemaRepair(client, prContent, rawOutput, options);
    }

    return { result: parsed as ReviewResult, rawOutput };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return { result: null, rawOutput: '', error: errorMessage };
  }
}

/**
 * Retry the OpenAI call with a schema repair instruction.
 */
async function retryWithSchemaRepair(
  client: OpenAI,
  prContent: string,
  previousOutput: string,
  options: ReviewOptions
): Promise<{ result: ReviewResult | null; rawOutput: string; error?: string }> {
  const { model, effort } = options;
  const apiEffort = mapEffortToOpenAI(effort);

  try {
    const response = await client.responses.create({
      model,
      reasoning: { effort: apiEffort },
      input: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: prContent },
        { role: 'assistant', content: previousOutput },
        { role: 'user', content: SCHEMA_REPAIR_INSTRUCTION },
      ],
      text: {
        format: {
          type: 'json_schema',
          name: REVIEW_SCHEMA.name,
          schema: REVIEW_SCHEMA.schema,
          strict: true,
        },
      },
    });

    const rawOutput = response.output_text || '';

    let parsed: unknown;
    try {
      parsed = JSON.parse(rawOutput);
    } catch {
      return {
        result: null,
        rawOutput,
        error: 'Failed to parse JSON after schema repair retry',
      };
    }

    const validation = validateReviewResult(parsed);
    if (!validation.valid) {
      return {
        result: null,
        rawOutput,
        error: `Schema validation failed after retry: ${validation.errors}`,
      };
    }

    return { result: parsed as ReviewResult, rawOutput };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return { result: null, rawOutput: '', error: `Retry failed: ${errorMessage}` };
  }
}

/**
 * Create a fallback review result for when the API fails.
 */
export function createFallbackResult(error: string, rawOutput?: string): ReviewResult {
  return {
    summary: 'Unable to complete automated review due to an error.',
    risk: {
      level: 'medium',
      rationale: 'Review could not be completed; manual review recommended.',
    },
    findings: [],
    tests: { add: [], run: [] },
    questions: [],
    coverage_note: `Error during review: ${error}${rawOutput ? '\n\nRaw output was captured for debugging.' : ''}`,
  };
}
