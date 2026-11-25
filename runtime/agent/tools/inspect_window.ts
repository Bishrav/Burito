import { calls } from 'eve/events';
import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const inspectWindow = defineTool({
  description: 'After desktop_windows identifies one unique target and the owner asks what that app shows, request one approval that will unminimize/focus that exact window and immediately capture only its active window for local OCR. Provide the exact internalId from the latest snapshot. The result includes tab_strip_candidate_lines from the top 15% of the window for tab-bar questions; these are OCR candidates, not a verified count. After one successful capture, answer the owner instead of ending on the tool result. It does not click, type, or store the screenshot.',
  inputSchema: z.object({
    internalId: z.string().regex(/^[0-9a-fA-F-]{36}$/),
  }),
  approval: {
    prompt: () => 'Unminimize/focus the selected app window (this may switch virtual desktops), then immediately capture that active window once for local OCR? The temporary image is deleted; OCR text may remain in local chat history.',
    request: async (ctx) => {
      await hostAccess({ action: 'screen_reserve', session_id: ctx.session.id,
        turn_id: ctx.session.turn.id, call_id: ctx.callId }, ctx.abortSignal);
      return 'user-approval';
    },
  },
  execute: (input, ctx) => hostAccess({ action: 'inspect_window', ...input,
    session_id: ctx.session.id, turn_id: ctx.session.turn.id, call_id: ctx.callId }, ctx.abortSignal, true),
});

export default defineDynamic((ctx) => {
  if (process.env.BURITO_PC_ACCESS !== '1' || process.env.BURITO_DESKTOP_CONTROL !== '1' ||
      process.env.BURITO_SCREEN_READ !== '1') return null;
  if (ctx.turn?.id && calls(ctx.view, { name: 'read_screen', turnId: ctx.turn.id }).length > 0) return null;
  if (ctx.turn?.id && calls(ctx.view, { name: 'inspect_window', turnId: ctx.turn.id }).length > 0) return null;
  if (ctx.turn?.id && calls(ctx.view, { name: 'browser_search', turnId: ctx.turn.id }).length > 0) return null;
  return inspectWindow;
});