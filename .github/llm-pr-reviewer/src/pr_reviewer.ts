/**
 * LLM PR Reviewer - Main Entrypoint
 * Orchestrates the PR review process.
 */

import * as fs from 'fs';
import { Octokit } from '@octokit/rest';
import OpenAI from 'openai';
import { buildPRPacket, formatPRPacketForPrompt, isPRLarge } from './pr_packet';
import { callOpenAIReview, createFallbackResult } from './openai_review';
import { renderReviewMarkdown, renderFallbackMarkdown } from './render';
import { upsertPRComment } from './github_comments';
import { emitAnnotations, emitSummaryAnnotation } from './annotations';
import { ReviewResult } from './types';

interface Config {
  openaiApiKey: string;
  ghToken: string;
  repo: string;
  prNumber: number;
  headSha: string;
  model: string;
  effort: 'low' | 'medium' | 'high' | 'xhigh';
  summaryFile?: string;
}

function getConfig(): Config {
  const openaiApiKey = process.env.OPENAI_API_KEY;
  const ghToken = process.env.GH_TOKEN;
  const repo = process.env.REPO;
  const prNumber = process.env.PR_NUMBER;
  const headSha = process.env.HEAD_SHA;
  const model = process.env.REVIEW_MODEL || 'gpt-5.2';
  const effort = (process.env.REVIEW_EFFORT || 'high') as Config['effort'];
  const summaryFile = process.env.GITHUB_STEP_SUMMARY;

  if (!openaiApiKey) {
    throw new Error('OPENAI_API_KEY environment variable is required');
  }
  if (!ghToken) {
    throw new Error('GH_TOKEN environment variable is required');
  }
  if (!repo) {
    throw new Error('REPO environment variable is required');
  }
  if (!prNumber) {
    throw new Error('PR_NUMBER environment variable is required');
  }
  if (!headSha) {
    throw new Error('HEAD_SHA environment variable is required');
  }

  const [owner, repoName] = repo.split('/');
  if (!owner || !repoName) {
    throw new Error('REPO must be in format owner/repo');
  }

  return {
    openaiApiKey,
    ghToken,
    repo,
    prNumber: parseInt(prNumber, 10),
    headSha,
    model,
    effort,
    summaryFile,
  };
}

function writeToSummary(summaryFile: string | undefined, content: string): void {
  if (summaryFile) {
    try {
      fs.appendFileSync(summaryFile, content + '\n');
      console.log('Wrote review to job summary');
    } catch (error) {
      console.error('Failed to write to job summary:', error);
    }
  }
}

async function main(): Promise<void> {
  console.log('Starting LLM PR Review...');

  let config: Config;
  try {
    config = getConfig();
  } catch (error) {
    console.error('Configuration error:', error instanceof Error ? error.message : error);
    // Still succeed the job (advisory only)
    process.exit(0);
  }

  const [owner, repoName] = config.repo.split('/');

  // Initialize clients
  const octokit = new Octokit({ auth: config.ghToken });
  const openai = new OpenAI({ apiKey: config.openaiApiKey });

  console.log(`Reviewing PR #${config.prNumber} in ${config.repo}`);
  console.log(`Model: ${config.model}, Effort: ${config.effort}`);

  // Step 1: Build PR packet
  console.log('Fetching PR data...');
  let prPacket;
  try {
    // Hard caps prevent accidentally oversized prompts (cost/latency/API failures)
    const MAX_PATCH_CAP = 100000; // 100KB per file
    const MAX_PACKET_CAP = 1000000; // 1MB total
    const reviewConfig: Partial<import('./types').ReviewConfig> = {};
    if (process.env.REVIEW_MAX_PATCH_SIZE) {
      const v = parseInt(process.env.REVIEW_MAX_PATCH_SIZE, 10);
      if (Number.isFinite(v) && v > 0) {
        reviewConfig.maxPatchSize = Math.min(v, MAX_PATCH_CAP);
      } else {
        console.warn(`Ignoring invalid REVIEW_MAX_PATCH_SIZE: "${process.env.REVIEW_MAX_PATCH_SIZE}"`);
      }
    }
    if (process.env.REVIEW_MAX_PACKET_SIZE) {
      const v = parseInt(process.env.REVIEW_MAX_PACKET_SIZE, 10);
      if (Number.isFinite(v) && v > 0) {
        reviewConfig.maxPacketSize = Math.min(v, MAX_PACKET_CAP);
      } else {
        console.warn(`Ignoring invalid REVIEW_MAX_PACKET_SIZE: "${process.env.REVIEW_MAX_PACKET_SIZE}"`);
      }
    }
    prPacket = await buildPRPacket(octokit, {
      owner,
      repo: repoName,
      prNumber: config.prNumber,
      config: reviewConfig,
    });
    console.log(`PR has ${prPacket.files.length} files, ${prPacket.totalAdditions}+ / ${prPacket.totalDeletions}-`);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('Failed to fetch PR data:', errorMessage);

    const fallbackMarkdown = renderFallbackMarkdown(
      `Failed to fetch PR data: ${errorMessage}`,
      config.headSha
    );
    writeToSummary(config.summaryFile, fallbackMarkdown);

    // Advisory only - don't fail the job
    process.exit(0);
  }

  // Step 2: Determine effort level
  let effort = config.effort;
  if (isPRLarge(prPacket) && effort !== 'xhigh') {
    console.log('PR is large, upgrading effort to xhigh');
    effort = 'xhigh';
  }

  // Step 3: Format packet for LLM
  const prContent = formatPRPacketForPrompt(prPacket);
  console.log(`PR packet size: ${prContent.length} characters`);

  // Step 4: Call OpenAI
  console.log('Calling OpenAI for review...');
  let reviewResult: ReviewResult;
  let rawOutput: string = '';

  try {
    const response = await callOpenAIReview(openai, prContent, {
      model: config.model,
      effort,
    });

    if (response.result) {
      reviewResult = response.result;
      rawOutput = response.rawOutput;
      console.log('Review completed successfully');
    } else {
      console.error('OpenAI review failed:', response.error);
      reviewResult = createFallbackResult(response.error || 'Unknown error', response.rawOutput);
      rawOutput = response.rawOutput;
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('OpenAI call failed:', errorMessage);
    reviewResult = createFallbackResult(errorMessage);
  }

  // Step 5: Render markdown
  let markdown: string;
  if (reviewResult.coverage_note?.startsWith('Error during review:')) {
    // This is a fallback result
    // Log raw output to Actions logs (not PR comments) for debugging
    if (rawOutput) {
      console.log('Raw LLM output (for debugging):');
      console.log(rawOutput);
    }
    markdown = renderFallbackMarkdown(
      reviewResult.coverage_note.replace('Error during review: ', ''),
      config.headSha
    );
  } else {
    markdown = renderReviewMarkdown(reviewResult, config.headSha);
  }

  // Step 6: Write to job summary (always)
  console.log('Writing to job summary...');
  writeToSummary(config.summaryFile, markdown);

  // Step 7: Post/update PR comment (best effort)
  console.log('Posting PR comment...');
  const commentResult = await upsertPRComment(
    octokit,
    {
      owner,
      repo: repoName,
      issueNumber: config.prNumber,
    },
    markdown
  );

  if (commentResult.success) {
    console.log(`PR comment ${commentResult.commentId ? 'updated' : 'created'} successfully`);
  } else {
    console.warn('Failed to post PR comment:', commentResult.error);
    console.warn('Review is still available in the job summary.');
  }

  // Step 8: Emit annotations
  console.log('Emitting annotations...');

  // Count findings by severity
  const findingCounts = {
    blockers: reviewResult.findings.filter((f) => f.severity === 'blocker').length,
    majors: reviewResult.findings.filter((f) => f.severity === 'major').length,
    minors: reviewResult.findings.filter((f) => f.severity === 'minor').length,
    nits: reviewResult.findings.filter((f) => f.severity === 'nit').length,
  };

  emitSummaryAnnotation(reviewResult.risk.level, findingCounts);
  emitAnnotations(reviewResult.findings);

  console.log('LLM PR Review completed.');

  // Always exit successfully (advisory only)
  process.exit(0);
}

// Run main
main().catch((error) => {
  console.error('Unhandled error:', error);
  // Advisory only - don't fail the job
  process.exit(0);
});
