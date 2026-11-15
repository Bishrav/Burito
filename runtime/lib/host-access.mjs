import { execFile } from 'node:child_process';
import { readSettings } from './settings.mjs';

export async function hostAccess(request, signal, approvedLaunch = false) {
  // Enforce local mode and the owner's access switch outside the model prompt.
  readSettings(process.env);
  if (process.env.BURITO_PC_ACCESS === '0') throw new Error('PC file/application tools are disabled for this chat.');
  if (!process.env.BURITO_PROJECT_ROOT || !process.env.BURITO_PYTHON) {
    throw new Error('Start with python3 -m burito chat to configure the local bridge.');
  }
  return new Promise((resolve, reject) => {
    const child = execFile(process.env.BURITO_PYTHON, ['-m', 'burito', 'access-bridge'], {
      cwd: process.env.BURITO_PROJECT_ROOT,
      env: { ...process.env, BURITO_APPROVED_APP_LAUNCH: approvedLaunch ? '1' : '0' },
      timeout: 15000, maxBuffer: 65536, signal,
    }, (error, stdout, stderr) => {
      if (error) return reject(new Error(stderr.trim().slice(0, 500) || error.message));
      try { resolve(JSON.parse(stdout)); } catch { reject(new Error('Local bridge returned invalid JSON.')); }
    });
    child.stdin.on('error', () => {});
    child.stdin.end(JSON.stringify(request));
  });
}
