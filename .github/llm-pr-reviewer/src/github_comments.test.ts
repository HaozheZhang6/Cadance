/**
 * Tests for GitHub Comments module
 */

import { findMarkerComment, upsertPRComment, deleteMarkerComment } from './github_comments';
import { COMMENT_MARKER } from './render';

// Mock Octokit with pagination support
const createMockOctokit = (options: {
  comments?: Array<{ id: number; body: string }>;
  createError?: Error;
  updateError?: Error;
  listError?: Error;
  usePagination?: boolean;
}) => {
  const { comments = [], createError, updateError, listError, usePagination = true } = options;

  return {
    issues: {
      listComments: jest.fn().mockImplementation(() => {
        if (listError) throw listError;
        return Promise.resolve({ data: comments });
      }),
      createComment: jest.fn().mockImplementation(({ body }) => {
        if (createError) throw createError;
        return Promise.resolve({ data: { id: 999, body } });
      }),
      updateComment: jest.fn().mockImplementation(({ comment_id, body }) => {
        if (updateError) throw updateError;
        return Promise.resolve({ data: { id: comment_id, body } });
      }),
      deleteComment: jest.fn().mockResolvedValue({}),
    },
    // Mock paginate function - returns all comments
    paginate: jest.fn().mockImplementation(async () => {
      if (listError) throw listError;
      return comments;
    }),
  } as any;
};

describe('findMarkerComment', () => {
  const options = { owner: 'test', repo: 'repo', issueNumber: 1 };

  it('should return null when no comments exist', async () => {
    const octokit = createMockOctokit({ comments: [] });
    const result = await findMarkerComment(octokit, options);

    expect(result).toBeNull();
    // Should use paginate for fetching comments
    expect(octokit.paginate).toHaveBeenCalled();
  });

  it('should return null when no comment has the marker', async () => {
    const octokit = createMockOctokit({
      comments: [
        { id: 1, body: 'Regular comment' },
        { id: 2, body: 'Another comment' },
      ],
    });
    const result = await findMarkerComment(octokit, options);

    expect(result).toBeNull();
  });

  it('should return the comment ID when marker comment exists', async () => {
    const octokit = createMockOctokit({
      comments: [
        { id: 1, body: 'Regular comment' },
        { id: 42, body: `${COMMENT_MARKER}\n# LLM Review` },
        { id: 3, body: 'Another comment' },
      ],
    });
    const result = await findMarkerComment(octokit, options);

    expect(result).toBe(42);
  });

  it('should return null on API error', async () => {
    const octokit = createMockOctokit({
      listError: new Error('API error'),
    });
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

    const result = await findMarkerComment(octokit, options);

    expect(result).toBeNull();
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it('should find marker comment when it is beyond first 100 comments (pagination)', async () => {
    // Create 150 comments, with the marker comment at position 120
    const manyComments = Array.from({ length: 150 }, (_, i) => ({
      id: i + 1,
      body: i === 120 ? `${COMMENT_MARKER}\n# LLM Review` : `Comment ${i}`,
    }));

    const octokit = createMockOctokit({ comments: manyComments });
    const result = await findMarkerComment(octokit, options);

    // Should find the marker comment at position 120 (id = 121)
    expect(result).toBe(121);
    // Should have used pagination
    expect(octokit.paginate).toHaveBeenCalled();
  });
});

describe('upsertPRComment', () => {
  const options = { owner: 'test', repo: 'repo', issueNumber: 1 };
  const body = `${COMMENT_MARKER}\n# Review`;

  it('should create a new comment when none exists', async () => {
    const octokit = createMockOctokit({ comments: [] });
    const result = await upsertPRComment(octokit, options, body);

    expect(result.success).toBe(true);
    expect(result.commentId).toBe(999);
    expect(octokit.issues.createComment).toHaveBeenCalledWith({
      owner: 'test',
      repo: 'repo',
      issue_number: 1,
      body,
    });
  });

  it('should update existing comment when marker exists', async () => {
    const octokit = createMockOctokit({
      comments: [{ id: 42, body: `${COMMENT_MARKER}\nOld review` }],
    });
    const result = await upsertPRComment(octokit, options, body);

    expect(result.success).toBe(true);
    expect(result.commentId).toBe(42);
    expect(octokit.issues.updateComment).toHaveBeenCalledWith({
      owner: 'test',
      repo: 'repo',
      comment_id: 42,
      body,
    });
    expect(octokit.issues.createComment).not.toHaveBeenCalled();
  });

  it('should return error on 403 permission denied', async () => {
    const octokit = createMockOctokit({
      comments: [],
      createError: new Error('403 Resource not accessible by integration'),
    });
    const result = await upsertPRComment(octokit, options, body);

    expect(result.success).toBe(false);
    expect(result.error).toContain('Permission denied');
    expect(result.error).toContain('403');
  });

  it('should return error on other failures', async () => {
    const octokit = createMockOctokit({
      comments: [],
      createError: new Error('Network error'),
    });
    const result = await upsertPRComment(octokit, options, body);

    expect(result.success).toBe(false);
    expect(result.error).toContain('Network error');
  });
});

describe('deleteMarkerComment', () => {
  const options = { owner: 'test', repo: 'repo', issueNumber: 1 };

  it('should return false when no marker comment exists', async () => {
    const octokit = createMockOctokit({ comments: [] });
    const result = await deleteMarkerComment(octokit, options);

    expect(result).toBe(false);
    expect(octokit.issues.deleteComment).not.toHaveBeenCalled();
  });

  it('should delete and return true when marker comment exists', async () => {
    const octokit = createMockOctokit({
      comments: [{ id: 42, body: `${COMMENT_MARKER}\nReview` }],
    });
    const result = await deleteMarkerComment(octokit, options);

    expect(result).toBe(true);
    expect(octokit.issues.deleteComment).toHaveBeenCalledWith({
      owner: 'test',
      repo: 'repo',
      comment_id: 42,
    });
  });
});
