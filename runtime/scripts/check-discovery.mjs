import { spawnSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { renameSync, unlinkSync, writeFileSync } from 'node:fs';

const result = spawnSync('eve', ['info', '--json'], { encoding: 'utf8' });
if (result.error) throw result.error;
if (result.status !== 0) {
  process.stderr.write(result.stderr ?? 'Eve discovery failed\n');
  process.exit(result.status ?? 1);
}
JSON.parse(result.stdout);

const temporary = `.eve-info.json.${randomUUID()}.tmp`;
try {
  writeFileSync(temporary, result.stdout, { flag: 'wx', mode: 0o600 });
  renameSync(temporary, '.eve-info.json');
} finally {
  try { unlinkSync(temporary); } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
}
