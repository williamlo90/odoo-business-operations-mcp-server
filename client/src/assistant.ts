import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('../../', import.meta.url));

export function runAssistant(packet: unknown): Promise<any> {
  const python = process.env.ASSISTANT_PYTHON ?? join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const args = ['-m', 'backend.assistant', '--stdio'];
  if (process.env.ASSISTANT_ENV_FILE) args.push('--env-file', process.env.ASSISTANT_ENV_FILE);
  if (process.env.ASSISTANT_RATE_FILE) args.push('--rate-file', process.env.ASSISTANT_RATE_FILE);
  return new Promise((resolve, reject) => {
    const child = spawn(python, args, { cwd: root, windowsHide: true, shell: false,
      stdio: ['pipe', 'pipe', 'pipe'], env: process.env });
    let data = Buffer.alloc(0);
    let settled = false;
    const fail = (code: string) => {
      if (!settled) { settled = true; child.kill(); reject(new Error(code)); }
    };
    const timeout = setTimeout(() => fail('assistant_timeout_check_task_state'), 90_000);
    child.stdout.on('data', (chunk: Buffer) => {
      data = Buffer.concat([data, chunk]);
      if (data.length > 262144) fail('assistant_output_too_large');
    });
    // Never relay Python tracebacks, environment values or downstream error bodies.
    child.stderr.resume();
    child.on('error', () => fail('assistant_process_unavailable'));
    child.stdin.on('error', () => fail('assistant_input_failed'));
    child.on('close', (code) => {
      clearTimeout(timeout);
      if (settled) return;
      try {
        const value = JSON.parse(data.toString('utf8'));
        if (code !== 0) {
          fail(typeof value.error === 'string' && /^[a-z_]+$/.test(value.error) ? value.error : 'assistant_failed');
          return;
        }
        const states = ['read', 'needs_input', 'awaiting_approval', 'verified', 'unknown', 'review', 'failed', 'dispatched'];
        if (!value.task_id || !states.includes(value.result?.status)) throw new Error();
        settled = true;
        resolve(value);
      } catch { fail('assistant_invalid_response'); }
    });
    const serialized = JSON.stringify(packet);
    if (Buffer.byteLength(serialized) > 16384) { fail('assistant_input_too_large'); return; }
    child.stdin.end(serialized);
  });
}
