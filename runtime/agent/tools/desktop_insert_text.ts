import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const desktopInsertText = defineTool({
  description: 'After desktop_windows identifies the exact destination window, insert owner-requested text at the caret in its currently focused accessible text field. This focuses that exact window and inserts without replacing existing text. Requires --enable-desktop-control and explicit approval showing the full text and destination.',
  inputSchema: z.object({
    internalId: z.string().regex(/^[0-9a-fA-F-]{36}$/),
    expected_caption: z.string().min(1).max(512),
    text: z.string().min(1).max(5000),
  }),
  approval: {
    request: always(),
    prompt: ({ input }) => `Focus the window ${JSON.stringify(input.expected_caption)} (${input.internalId}) and insert this exact text at its focused editable field? Existing text will not be replaced.\n\n${JSON.stringify(input.text)}`,
  },
  execute: (input, ctx) => hostAccess({ action: 'desktop_insert_text', ...input }, ctx.abortSignal, true),
});

export default defineDynamic(() =>
  process.env.BURITO_PC_ACCESS === '1' && process.env.BURITO_DESKTOP_CONTROL === '1'
    ? desktopInsertText : null,
);
