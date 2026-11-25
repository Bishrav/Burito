import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const browserFindTabs = defineTool({
  description: 'Find Brave tabs whose visible title matches the owner-provided phrase. Returns only matching tab IDs and titles, never URLs or page contents. Requires owner approval and the optional Brave tab-label permission.',
  inputSchema: z.object({ query: z.string().trim().min(1).max(100) }),
  approval: {
    request: always(),
    prompt: ({ input }) => `Look for Brave tabs with a title matching ${JSON.stringify(input.query)}? Only matching tab titles and temporary tab IDs will be shared; no URLs or page contents are read.`,
  },
  execute: (input, ctx) => hostAccess({ action: 'browser_find_tabs', ...input }, ctx.abortSignal, true),
});

export default defineDynamic(() => process.env.BURITO_PC_ACCESS === '1' && process.env.BURITO_BRAVE_TABS === '1' ? browserFindTabs : null);
