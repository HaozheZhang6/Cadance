/**
 * GitHub Comments Module
 * Creates and updates sticky PR comments.
 */

import { Octokit } from '@octokit/rest';
import { COMMENT_MARKER } from './render';

export interface CommentOptions {
  owner: string;
  repo: string;
  issueNumber: number; // PRs are issues in GitHub API
}

/**
 * Find an existing comment with the marker.
 * Uses pagination to search all comments on the issue/PR.
 */
export async function findMarkerComment(
  octokit: Octokit,
  options: CommentOptions
): Promise<number | null> {
  const { owner, repo, issueNumber } = options;

  try {
    // Paginate through all comments to find the marker
    // This handles PRs with >100 comments
    const comments = await octokit.paginate(octokit.issues.listComments, {
      owner,
      repo,
      issue_number: issueNumber,
      per_page: 100,
    });

    // Find comment with our marker
    const markerComment = comments.find((c) => c.body?.includes(COMMENT_MARKER));

    return markerComment?.id ?? null;
  } catch (error) {
    // Only log error message, not full object (may contain sensitive request details)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    const errorStatus = (error as any)?.status;
    console.error(`Error finding marker comment: ${errorMessage}${errorStatus ? ` (status: ${errorStatus})` : ''}`);
    return null;
  }
}

/**
 * Create or update the sticky PR comment.
 * Returns true if successful, false if failed (e.g., permissions issue).
 */
export async function upsertPRComment(
  octokit: Octokit,
  options: CommentOptions,
  body: string
): Promise<{ success: boolean; commentId?: number; error?: string }> {
  const { owner, repo, issueNumber } = options;

  try {
    // Check if we have an existing comment
    const existingCommentId = await findMarkerComment(octokit, options);

    if (existingCommentId) {
      // Update existing comment
      const { data: updated } = await octokit.issues.updateComment({
        owner,
        repo,
        comment_id: existingCommentId,
        body,
      });
      return { success: true, commentId: updated.id };
    } else {
      // Create new comment
      const { data: created } = await octokit.issues.createComment({
        owner,
        repo,
        issue_number: issueNumber,
        body,
      });
      return { success: true, commentId: created.id };
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);

    // Check for common permission errors
    if (errorMessage.includes('403') || errorMessage.includes('Resource not accessible')) {
      return {
        success: false,
        error: `Permission denied: ${errorMessage}. The workflow may not have write access to pull-requests.`,
      };
    }

    return { success: false, error: errorMessage };
  }
}

/**
 * Delete the marker comment if it exists (useful for cleanup).
 */
export async function deleteMarkerComment(
  octokit: Octokit,
  options: CommentOptions
): Promise<boolean> {
  const { owner, repo } = options;

  try {
    const existingCommentId = await findMarkerComment(octokit, options);

    if (existingCommentId) {
      await octokit.issues.deleteComment({
        owner,
        repo,
        comment_id: existingCommentId,
      });
      return true;
    }

    return false;
  } catch (error) {
    // Only log error message, not full object (may contain sensitive request details)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    const errorStatus = (error as any)?.status;
    console.error(`Error deleting marker comment: ${errorMessage}${errorStatus ? ` (status: ${errorStatus})` : ''}`);
    return false;
  }
}
