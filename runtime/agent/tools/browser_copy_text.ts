import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const browserCopyText = defineTool({
  description: 'Copy exact text supplied by the owner or extracted from the active Brave page into the system clipboard. Never read the clipboard. Requires --enable-browser-control, optional clipboard permission from the Burito extension popup, and a separate approval showing the full text for every copy.',
  inputSchema: z.object({ text: z.string().min(1).max(5000) }),
  approval: {
    request: always(),
    prompt: ({ input }) => `Copy this exact text to the system clipboard? This writes only; Burito cannot read your clipboard. The text is sent only over the local Brave extension connection.\n\n${JSON.stringify(input.text)}`,
  },
  execute: (input, ctx) => hostAccess({ action: 'browser_copy_text', text: input.text }, ctx.abortSignal, true),
});

export default defineDynamic((ctx) => {
  if (process.env.BURITO_PC_ACCESS !== '1' || process.env.BURITO_BROWSER_CONTROL !== '1') return null;
  const request = (ctx.turn?.input ?? [])
    .filter((part) => part.kind === 'text')
    .map((part) => part.text)
    .join(' ');
  return /\b(brave|browser|tab|url|website|webpage|web\s+site|gmail|youtube)\b/i.test(request)
    ? browserCopyText : null;
});