import { defineDynamic, defineTool } from 'eve/tools';
import { always } from 'eve/tools/approval';
import { z } from 'zod';
import { hostAccess } from '../../lib/host-access.mjs';

const browserPageAction = defineTool({
  description: 'Perform one page action after owner approval: click one uniquely matched visible label (pass it as target; for compatibility, a click label supplied as text is also accepted), fill one uniquely matched non-password field, press Enter/Tab/Escape in a named field, scroll, or navigate back/forward. Each action requires approval.',
  inputSchema: z.object({
    action: z.enum(['click_text', 'type_text', 'press_key', 'scroll', 'back', 'forward']),
    target: z.string().max(200).optional(),
    text: z.string().max(2000).optional(),
    key: z.enum(['Enter', 'Tab', 'Escape']).optional(),
    direction: z.enum(['up', 'down']).optional(),
    amount: z.number().int().min(50).max(2000).optional(),
  }),
  approval: {
    request: always(),
    prompt: ({ input }) => {
      const target = input.target || (input.action === 'click_text' ? input.text : undefined);
      const irreversible = input.action === 'click_text' && /\b(send|submit|publish|post|pay|buy|delete|remove|confirm|place order)\b/i.test(target || '');
      if (input.action === 'type_text') return `Type this exact text into the uniquely matching visible field ${JSON.stringify(input.target)} in the active Brave tab?\n\n${JSON.stringify(input.text)}\n\nThis does not submit the form.`;
      if (input.action === 'click_text') return `Click the one visible control matching ${JSON.stringify(target)} in the active Brave tab?${irreversible ? ' This may send information or make an external/destructive change.' : ''}`;
      if (input.action === 'press_key') return `Press ${input.key} in the visible field ${JSON.stringify(input.target)} in the active Brave tab? Enter may submit a form.`;
      if (input.action === 'scroll') return `Scroll ${input.direction} ${input.amount} pixels in the active Brave page?`;
      return `Navigate ${input.action} in the active Brave tab?`;
    },
  },
  execute: (input, ctx) => hostAccess({ action: 'browser_page_action', browser_action: input.action,
    target: input.target || (input.action === 'click_text' ? input.text : undefined),
    text: input.text, key: input.key, direction: input.direction,
    amount: input.amount }, ctx.abortSignal, true),
});

export default defineDynamic(() => process.env.BURITO_PC_ACCESS === '1' && process.env.BURITO_BROWSER_CONTROL === '1' ? browserPageAction : null);