import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import { defineAgent, defineDynamic } from 'eve';
import { readSettings } from '../lib/settings.mjs';

// Resolve at runtime, not build time. Missing configuration stops the turn.
export default defineAgent({
  defaultTools: false,
  model: defineDynamic(() => {
    const settings = readSettings(process.env);
    const local = createOpenAICompatible({
      name: 'burito-local', baseURL: settings.baseURL, includeUsage: true,
    });
    return {
      model: local(settings.model),
      modelContextWindowTokens: settings.contextTokens,
    };
  }),
});
