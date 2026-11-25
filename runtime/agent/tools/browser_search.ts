import { calls } from 'eve/events';
import { defineDynamic, defineTool } from 'eve/tools';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const browserSearch = defineTool({
  description: 'Search the exact owner-requested query in the regular Brave profile, then focus the active Brave window and capture it once with local OCR. Do not add conversation, memory, file, activity, or inferred context. Does not click results, submit forms, or download files.',
  inputSchema: z.object({
    query: z.string().trim().min(1).max(500).regex(/^[^\u0000-\u001f\u007f]+$/),
  }),
  approval: {
    prompt: ({ input }) => `Search Brave in your regular profile for this exact query: ${JSON.stringify(input.query)}? Burito will send the query to Brave Search over the internet, focus the active Brave window, and capture that window once with local OCR. The query may remain in your browser history. No result will be clicked, no form submitted, and no file downloaded.`,
    request: async (ctx) => {
      await hostAccess({ action: 'browser_search_reserve', session_id: ctx.session.id,
        turn_id: ctx.session.turn.id, call_id: ctx.callId }, ctx.abortSignal);
      return 'user-approval';
    },
  },
  execute: (input, ctx) => hostAccess({ action: 'browser_search', ...input,
    session_id: ctx.session.id, turn_id: ctx.session.turn.id, call_id: ctx.callId }, ctx.abortSignal, true),
});

export default defineDynamic((ctx) => {
  if (process.env.BURITO_PC_ACCESS !== '1' || process.env.BURITO_BROWSER_SEARCH !== '1') return null;
  // Do not let an agent retry a search in the same owner turn. One approved
  // invocation must produce one answer, even when the result is ambiguous.
  if (ctx.turn?.id && calls(ctx.view, { name: 'browser_search', turnId: ctx.turn.id }).length > 0) return null;
  return browserSearch;
});
