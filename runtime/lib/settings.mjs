export function readSettings(environment) {
  if ((environment.BURITO_MODE || 'local') !== 'local') {
    throw new Error('Cloud routing is not enabled in this milestone. Use local mode.');
  }
  const model = (environment.BURITO_LOCAL_MODEL || '').trim();
  if (!model) throw new Error('Choose an installed local model with --model.');
  const contextTokens = Number(environment.BURITO_CONTEXT_TOKENS);
  if (!Number.isInteger(contextTokens) || contextTokens < 4096 || contextTokens > 131072) {
    throw new Error('Set the context size actually allocated by your local model server.');
  }
  const endpoint = new URL(environment.BURITO_LOCAL_URL || 'http://127.0.0.1:11434/v1');
  if (!['http:', 'https:'].includes(endpoint.protocol) ||
      !['127.0.0.1', '[::1]'].includes(endpoint.hostname) ||
      endpoint.username || endpoint.password || endpoint.search || endpoint.hash) {
    throw new Error('Local mode requires a literal loopback HTTP endpoint without credentials or query parameters.');
  }
  return {
    model, contextTokens, baseURL: endpoint.href,
    lesson: environment.BURITO_LESSON_ID || 'home.honesty',
    includePersonal: environment.BURITO_INCLUDE_PERSONAL_MEMORY === '1',
    includeSystem: environment.BURITO_INCLUDE_SYSTEM !== '0',
    includeActivity: environment.BURITO_INCLUDE_ACTIVITY === '1',
    includeFeedback: environment.BURITO_INCLUDE_FEEDBACK === '1',
    includeProject: environment.BURITO_INCLUDE_PROJECT === '1',
    includeSuggestions: environment.BURITO_INCLUDE_SUGGESTIONS === '1',
    includeKnowledge: environment.BURITO_INCLUDE_KNOWLEDGE === '1',
  };
}
