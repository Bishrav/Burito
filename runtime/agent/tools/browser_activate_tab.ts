import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const browserActivateTab = defineTool({
  description: 'Activate one exact Brave tab from a recent browser_find_tabs result. The owner must approve the specific title and tab ID. Refuses if the tab disappeared or its title changed.',
  inputSchema: z.object({ tab_id: z.number().int().nonnegative(), expected_title: z.string().min(1).max(512) }),
  approval: {
    request: always(),
    prompt: ({ input }) => `Switch Brave to the tab titled ${JSON.stringify(input.expected_title)} (tab ID ${input.tab_id})?`,
  },
  execute: (input, ctx) => hostAccess({ action: 'browser_activate_tab', ...input }, ctx.abortSignal, true),
});

export default defineDynamic(() => process.env.BURITO_PC_ACCESS === '1' && process.env.BURITO_BRAVE_TABS === '1' ? browserActivateTab : null);