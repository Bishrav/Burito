import { calls } from 'eve/events';
import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const browserTabs = defineTool({
  description: 'Read only the current number of tabs from the installed Burito Brave extension. The extension sends a count only; it does not send tab titles, URLs, or page contents. Every read requires owner approval.',
  inputSchema: z.object({}),
  approval: {
    request: always(),
    prompt: () => 'Read the current open-tab count from the local Brave extension? Only the count is returned; no titles, URLs, or page contents are read.',
  },
  execute: (_input, ctx) => hostAccess({ action: 'browser_tabs' }, ctx.abortSignal, true),
});

export default defineDynamic((ctx) => {
  if (process.env.BURITO_PC_ACCESS !== '1' || process.env.BURITO_BRAVE_TABS !== '1') return null;
  if (ctx.turn?.id && calls(ctx.view, { name: 'browser_tabs', turnId: ctx.turn.id }).length > 0) return null;
  return browserTabs;
});
