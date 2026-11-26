import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const focusWindow = defineTool({
  description: 'After listing desktop_windows, request owner approval to unminimize and focus that exact Hyprland or KWin window. This may switch virtual desktops. Provide the exact internalId returned by the latest snapshot. This does not click, type, or read content.',
  inputSchema: z.object({
    internalId: z.string().regex(/^(?:[0-9a-fA-F-]{36}|hyprland:[1-9][0-9]{0,18})$/),
  }),
  approval: always(),
  execute: (input, ctx) => hostAccess({ action: 'focus_window', ...input }, ctx.abortSignal, Boolean(ctx.approval)),
});

export default defineDynamic(() =>
  process.env.BURITO_PC_ACCESS === '1' && process.env.BURITO_DESKTOP_CONTROL === '1'
    ? focusWindow : null,
);
