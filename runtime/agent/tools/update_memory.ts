import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';

const execute = promisify(execFile);

const updateMemory = defineTool({
  description: 'Correct one existing owner-provided personal memory. Call only when the owner explicitly asks to update or correct that saved fact. Use its exact ID and current text from personal_facts, and provide the complete corrected fact. Approval is always required.',
  inputSchema: z.object({
    memoryId: z.string().uuid(),
    expectedCurrentContent: z.string().min(1).max(20000),
    correctedContent: z.string().trim().min(1).max(20000),
  }),
  approval: {
    request: always(),
    prompt: ({ input }) =>
      `Update saved personal fact? Current: ${input.expectedCurrentContent} -> Replace with: ${input.correctedContent}`,
  },
  execute: async ({ memoryId, expectedCurrentContent, correctedContent }) => {
    const root = process.env.BURITO_PROJECT_ROOT;
    const python = process.env.BURITO_PYTHON;
    if (!root || !python) throw new Error('Burito project paths are not configured.');
    const { stdout } = await execute(python, [
      '-m', 'burito', 'correct', memoryId, correctedContent,
      '--expected', expectedCurrentContent,
    ], { cwd: root, timeout: 5000, maxBuffer: 16384 });
    if (!stdout.trim().includes('Memory corrected')) {
      throw new Error('Burito did not confirm the memory update.');
    }
    return { memoryId, status: 'updated' };
  },
});

export default defineDynamic(() =>
  process.env.BURITO_INCLUDE_PERSONAL_MEMORY === '1' &&
  process.env.BURITO_MEMORY_WRITES === '1'
    ? updateMemory
    : null,
);
