import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const browserNavigate = defineTool({
  description: 'Open the exact owner-requested HTTP/HTTPS URL in the active Brave tab. Use this when the owner asks to open a website or a tab search finds no matching site. Does not read page contents; page reading and site permission are separate.',
  inputSchema: z.object({
    url: z.string().trim().min(8).max(2000).url().refine((value) => {
      try {
        const parsed = new URL(value);
        return ['http:', 'https:'].includes(parsed.protocol) && !parsed.username && !parsed.password;
      } catch { return false; }
    }, 'Only HTTP/HTTPS URLs without embedded credentials are allowed.'),
  }),
  approval: {
    request: always(),
    prompt: ({ input }) => `Open this exact URL in the active Brave tab?\n\n${JSON.stringify(input.url)}\n\nThis changes the active tab's page. Burito will not read the page until a separate approved request.`,
  },
  execute: (input, ctx) => hostAccess({ action: 'browser_page_action', browser_action: 'navigate', ...input }, ctx.abortSignal, true),
});

export default defineDynamic(() => process.env.BURITO_PC_ACCESS === '1' && process.env.BURITO_BROWSER_CONTROL === '1' ? browserNavigate : null);
