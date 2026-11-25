import { calls } from 'eve/events';
import { defineDynamic, defineTool } from 'eve/tools';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const readScreen = defineTool({
  description: 'Capture the current full screen or the currently active application window at most once per user message and extract visible text with local OCR. For a named app, first use desktop_windows, then request approval to focus the exact app window, then capture scope active_window. The capture requires owner approval. The image is temporary and deleted after OCR; only recognized text and coordinates are returned. OCR does not describe visual objects. After one result, stop calling this tool and answer.',
  inputSchema: z.object({ scope: z.enum(['full_screen', 'active_window']) }),
  approval: {
    prompt: () => 'Capture the requested screen scope once and extract text locally? The image is temporary; recognized text may remain in local chat history.',
    request: async (ctx) => {
      await hostAccess({ action: 'screen_reserve', session_id: ctx.session.id,
        turn_id: ctx.session.turn.id, call_id: ctx.callId }, ctx.abortSignal);
      return 'user-approval';
    },
  },
  execute: (input, ctx) => hostAccess({ action: 'screen_read', ...input,
    session_id: ctx.session.id, turn_id: ctx.session.turn.id, call_id: ctx.callId }, ctx.abortSignal),
});

export default defineDynamic((ctx) => {
  if (process.env.BURITO_PC_ACCESS !== '1' || process.env.BURITO_SCREEN_READ !== '1') return null;
  if (!ctx.turn?.id || calls(ctx.view, { name: 'read_screen', turnId: ctx.turn.id }).length > 0) return null;
  if (calls(ctx.view, { name: 'inspect_window', turnId: ctx.turn.id }).length > 0) return null;
  if (calls(ctx.view, { name: 'browser_search', turnId: ctx.turn.id }).length > 0) return null;
  const request = (ctx.turn.input ?? []).filter((part) => part.kind === 'text').map((part) => part.text).join(' ');
  const explicitlyDesktop = /\b(screen|desktop|monitor|full\s+screen|ocr)\b/i.test(request);
  const namesBrowser = /\b(brave|browser|tab|url|website|webpage|web\s+site|gmail|youtube)\b/i.test(request);
  const isPageFollowup = /\b(again|recheck|check(?:\s+the)?\s+page|read(?:\s+the)?\s+page|what(?:'s| is)\s+(?:on|in)\s+(?:it|the\s+page))\b/i.test(request);
  const refersToFirstPageItem = /\b(first|top)\b.{0,35}\b(video|result|item|link)\b/i.test(request)
    || /\b(open|play|watch|click)\b.{0,35}\b(video|result|item|link)\b/i.test(request);
  const allCalls = calls(ctx.view);
  const latestBrowser = allCalls.filter((call) =>
    ['browser_read_page', 'browser_navigate', 'browser_page_action', 'browser_activate_tab'].includes(call.name),
  ).at(-1);
  const latestDesktopCapture = allCalls.filter((call) =>
    ['read_screen', 'inspect_window'].includes(call.name),
  ).at(-1);
  const browserContextIsCurrent = Boolean(latestBrowser)
    && (!latestDesktopCapture || latestBrowser.startedAt >= latestDesktopCapture.startedAt);
  if (!explicitlyDesktop && (namesBrowser || ((isPageFollowup || refersToFirstPageItem) && browserContextIsCurrent))) return null;
  return readScreen;
});
