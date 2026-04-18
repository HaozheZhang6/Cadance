/**
 * Quick test script to verify OpenAI integration works.
 * Run with: npx ts-node test-openai.ts
 */

import OpenAI from 'openai';
import { callOpenAIReview, validateReviewResult } from './src/openai_review';
import { renderReviewMarkdown } from './src/render';

const SAMPLE_PR_CONTENT = `
# PR Title: Add user authentication feature

## PR Description
This PR adds basic user authentication with JWT tokens.

## Summary: 45 additions, 3 deletions across 2 files

## Changed Files
### src/auth.ts (added, +40/-0)
\`\`\`diff
+import jwt from 'jsonwebtoken';
+
+const SECRET = process.env.JWT_SECRET || 'dev-secret';
+
+export function generateToken(userId: string): string {
+  return jwt.sign({ userId }, SECRET, { expiresIn: '1h' });
+}
+
+export function verifyToken(token: string): { userId: string } | null {
+  try {
+    return jwt.verify(token, SECRET) as { userId: string };
+  } catch {
+    return null;
+  }
+}
+
+export async function authenticateUser(email: string, password: string) {
+  const user = await findUserByEmail(email);
+  if (!user) return null;
+  
+  // Check password
+  if (password === user.password) {  // TODO: use bcrypt
+    return generateToken(user.id);
+  }
+  return null;
+}
\`\`\`

### src/routes.ts (modified, +5/-3)
\`\`\`diff
 import express from 'express';
+import { authenticateUser, verifyToken } from './auth';
 
 const router = express.Router();
 
+router.post('/login', async (req, res) => {
+  const { email, password } = req.body;
+  const token = await authenticateUser(email, password);
+  if (token) {
+    res.json({ token });
+  } else {
+    res.status(401).json({ error: 'Invalid credentials' });
+  }
+});
\`\`\`
`;

async function main() {
  console.log('=== LLM PR Reviewer - OpenAI Integration Test ===\n');

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.error('ERROR: OPENAI_API_KEY environment variable is not set.');
    console.error('Run with: OPENAI_API_KEY=sk-... npx ts-node test-openai.ts');
    process.exit(1);
  }

  console.log('OpenAI API key found (starts with:', apiKey.substring(0, 7) + '...)');
  console.log('Model: gpt-5.2');
  console.log('Effort: medium (for faster testing)\n');

  const client = new OpenAI({ apiKey });

  console.log('Sending sample PR for review...\n');
  const startTime = Date.now();

  try {
    const response = await callOpenAIReview(client, SAMPLE_PR_CONTENT, {
      model: 'gpt-5.2',
      effort: 'medium',
    });

    const duration = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log(`Response received in ${duration}s\n`);

    if (response.error) {
      console.error('ERROR:', response.error);
      console.log('\nRaw output:', response.rawOutput.substring(0, 500));
      process.exit(1);
    }

    if (!response.result) {
      console.error('ERROR: No result returned');
      process.exit(1);
    }

    // Validate the result
    const validation = validateReviewResult(response.result);
    console.log('Schema validation:', validation.valid ? 'PASSED' : 'FAILED');
    if (!validation.valid) {
      console.error('Validation errors:', validation.errors);
    }

    console.log('\n=== Review Result ===\n');
    console.log('Summary:', response.result.summary);
    console.log('Risk Level:', response.result.risk.level.toUpperCase());
    console.log('Risk Rationale:', response.result.risk.rationale);
    console.log('Findings:', response.result.findings.length);
    
    for (const finding of response.result.findings) {
      console.log(`  - [${finding.severity.toUpperCase()}] ${finding.title}`);
      console.log(`    File: ${finding.file}`);
    }

    console.log('Tests to add:', response.result.tests.add.length);
    console.log('Questions:', response.result.questions.length);
    console.log('Coverage Note:', response.result.coverage_note.substring(0, 100) + '...');

    console.log('\n=== Rendered Markdown Preview ===\n');
    const markdown = renderReviewMarkdown(response.result, 'abc1234');
    // Show first 1500 chars of markdown
    console.log(markdown.substring(0, 1500) + '\n...[truncated]');

    console.log('\n=== TEST PASSED ===');
    console.log('OpenAI integration is working correctly!');

  } catch (error) {
    console.error('ERROR:', error);
    process.exit(1);
  }
}

main();
