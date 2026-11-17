import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';

const execute = promisify(execFile);

const rememberDefinition = defineTool({
  description: 'Save an owner-explained term and definition to Burito’s private local glossary. Call only after the owner explicitly asks to save it. This tool always requires owner approval; the approved input is stored verbatim.',
  inputSchema: z.object({
    term: z.string().trim().min(1).max(160),
    definition: z.string().trim().min(1).max(4000),
  }),
  approval: always(),
  execute: async ({ term, definition }) => {
    const root = process.env.BURITO_PROJECT_ROOT;
    const python = process.env.BURITO_PYTHON;
    if (!root || !python) throw new Error('Burito project paths are not configured.');
    const { stdout } = await execute(python, [
      '-m', 'burito', 'glossary', 'define', term, definition,
      '--source', 'owner-confirmed-conversation',
    ], { cwd: root, timeout: 5000, maxBuffer: 16384 });
    return JSON.parse(stdout);
  },
});

export default defineDynamic(() =>
  process.env.BURITO_INCLUDE_PERSONAL_MEMORY === '1' &&
  process.env.BURITO_GLOSSARY_WRITES === '1'
    ? rememberDefinition
    : null,
);
