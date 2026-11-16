import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const openApplication = defineTool({
  description: 'Request launching a registered desktop application after owner approval. First get its exact app_id and sha256 from applications. Does not prove a window opened or allow controlling the app.',
  inputSchema: z.object({ app_id: z.string().max(300), sha256: z.string().regex(/^[a-f0-9]{64}$/) }),
  approval: always(),
  execute: (input, ctx) => hostAccess({ action: 'launch', ...input }, ctx.abortSignal, true),
});

export default defineDynamic(() => process.env.BURITO_PC_ACCESS === '1' ? openApplication : null);
