import { defineDynamic, defineTool } from 'eve/tools';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const desktopWindows = defineTool({
  description: 'MANDATORY for requests such as “list the current windows”, “what windows are open”, or checking whether a named app has a window: call this tool once and report its result. Lists on-demand KDE Wayland managed application windows with internalId, resourceClass, caption, desktop, minimized state, active state, and current-desktop state. This is a current snapshot only; it does not prove a tray/background process is absent. If it errors, report the actual error and stop; do not substitute screen capture or speculate.',
  inputSchema: z.object({}),
  execute: (_input, ctx) => hostAccess({ action: 'windows' }, ctx.abortSignal),
});

export default defineDynamic(() =>
  process.env.BURITO_PC_ACCESS === '1' && process.env.BURITO_DESKTOP_CONTROL === '1'
    ? desktopWindows : null,
);
