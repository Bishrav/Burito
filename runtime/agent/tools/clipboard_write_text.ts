import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const clipboardWriteText = defineTool({
  description: 'Write exact owner-provided or screen/page-extracted text to the local system clipboard. This is write-only and does not require an open browser. Requires --enable-desktop-control, a local wl-copy or xclip executable, and separate approval showing the full text for every write.',
  inputSchema: z.object({ text: z.string().min(1).max(5000) }),
  approval: {
    request: always(),
    prompt: ({ input }) => `Copy this exact text to the local system clipboard? Burito can write but cannot read clipboard contents.\n\n${JSON.stringify(input.text)}`,
  },
  execute: (input, ctx) => hostAccess({ action: 'clipboard_write_text', text: input.text }, ctx.abortSignal, true),
});

export default defineDynamic(() =>
  process.env.BURITO_PC_ACCESS === '1' && process.env.BURITO_DESKTOP_CONTROL === '1'
    ? clipboardWriteText : null,
);
