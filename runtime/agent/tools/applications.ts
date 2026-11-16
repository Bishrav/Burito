import { defineDynamic, defineTool } from 'eve/tools';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const applications = defineTool({
  description: 'List registered desktop applications by optional name query. Returns exact app IDs and launcher hashes. This does not inspect app windows or execute an application.',
  inputSchema: z.object({ query: z.string().max(200).optional() }),
  execute: (input, ctx) => hostAccess({ action: 'apps', ...input }, ctx.abortSignal),
});

export default defineDynamic(() => process.env.BURITO_PC_ACCESS === '1' ? applications : null);
