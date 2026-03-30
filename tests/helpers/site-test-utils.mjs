import { access, readFile } from 'node:fs/promises';
import { spawn, spawnSync } from 'node:child_process';
import net from 'node:net';

const NPM_COMMAND = process.platform === 'win32' ? 'npm.cmd' : 'npm';

export async function readText(path) {
  return readFile(path, 'utf8');
}

export async function pathExists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

export function countOccurrences(text, needle) {
  if (!needle) {
    return 0;
  }

  return text.split(needle).length - 1;
}

export function parseCssVariables(css, scopeSelector) {
  const block = extractBlock(css, scopeSelector);
  const variables = new Map();
  const variablePattern = /(--[\w-]+)\s*:\s*([^;]+);/g;
  let match;

  while ((match = variablePattern.exec(block)) !== null) {
    variables.set(match[1], match[2].trim());
  }

  return variables;
}

export function extractBlock(text, marker) {
  const markerIndex = text.indexOf(marker);
  if (markerIndex === -1) {
    throw new Error(`Could not find block marker: ${marker}`);
  }

  const braceStart = text.indexOf('{', markerIndex);
  if (braceStart === -1) {
    throw new Error(`Could not find opening brace for block marker: ${marker}`);
  }

  let depth = 0;
  for (let index = braceStart; index < text.length; index += 1) {
    const char = text[index];

    if (char === '{') {
      depth += 1;
    } else if (char === '}') {
      depth -= 1;
      if (depth === 0) {
        return text.slice(braceStart + 1, index);
      }
    }
  }

  throw new Error(`Could not find closing brace for block marker: ${marker}`);
}

export function findRuleBlock(css, selector, { within } = {}) {
  const source = within ?? css;
  const rulePattern = /([^{}]+)\{([^{}]*)\}/g;
  let match;

  while ((match = rulePattern.exec(source)) !== null) {
    const selectors = match[1]
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);

    if (selectors.includes(selector)) {
      return match[2];
    }
  }

  return null;
}

export function getDeclarationValue(block, property) {
  if (!block) {
    return null;
  }

  const pattern = new RegExp(`${escapeRegExp(property)}\\s*:\\s*([^;]+);`);
  const match = block.match(pattern);
  return match ? match[1].trim() : null;
}

export function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function hexToRgb(hex) {
  const value = hex.replace('#', '').trim();

  if (value.length === 3) {
    return {
      r: Number.parseInt(value[0] + value[0], 16),
      g: Number.parseInt(value[1] + value[1], 16),
      b: Number.parseInt(value[2] + value[2], 16),
      a: 1,
    };
  }

  if (value.length === 6) {
    return {
      r: Number.parseInt(value.slice(0, 2), 16),
      g: Number.parseInt(value.slice(2, 4), 16),
      b: Number.parseInt(value.slice(4, 6), 16),
      a: 1,
    };
  }

  throw new Error(`Unsupported hex color: ${hex}`);
}

export function parseColor(color) {
  const value = color.trim();

  if (value.startsWith('#')) {
    return hexToRgb(value);
  }

  const rgbaMatch = value.match(
    /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/i,
  );
  if (rgbaMatch) {
    return {
      r: Number.parseFloat(rgbaMatch[1]),
      g: Number.parseFloat(rgbaMatch[2]),
      b: Number.parseFloat(rgbaMatch[3]),
      a: rgbaMatch[4] ? Number.parseFloat(rgbaMatch[4]) : 1,
    };
  }

  throw new Error(`Unsupported color format: ${color}`);
}

export function compositeColors(foreground, background) {
  const alpha = foreground.a ?? 1;
  return {
    r: foreground.r * alpha + background.r * (1 - alpha),
    g: foreground.g * alpha + background.g * (1 - alpha),
    b: foreground.b * alpha + background.b * (1 - alpha),
    a: 1,
  };
}

function channelToLinear(channel) {
  const normalized = channel / 255;
  return normalized <= 0.03928
    ? normalized / 12.92
    : ((normalized + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(color) {
  return (
    0.2126 * channelToLinear(color.r) +
    0.7152 * channelToLinear(color.g) +
    0.0722 * channelToLinear(color.b)
  );
}

export function contrastRatio(foreground, background) {
  const lighter = Math.max(relativeLuminance(foreground), relativeLuminance(background));
  const darker = Math.min(relativeLuminance(foreground), relativeLuminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

export function runNpmScript(rootDir, scriptName) {
  const result = spawnSync(NPM_COMMAND, ['run', scriptName], {
    cwd: rootDir,
    encoding: 'utf8',
    env: {
      ...process.env,
      CI: '1',
    },
  });

  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
    error: result.error ?? null,
  };
}

export function canBindLocalPort(host = '127.0.0.1') {
  return new Promise((resolve) => {
    const server = net.createServer();

    server.once('error', (error) => {
      resolve({ ok: false, error });
    });

    server.listen(0, host, () => {
      server.close(() => {
        resolve({ ok: true, error: null });
      });
    });
  });
}

export async function startDevServer(rootDir, port = 4321) {
  const child = spawn(NPM_COMMAND, ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(port)], {
    cwd: rootDir,
    env: {
      ...process.env,
      CI: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  let stdout = '';
  let stderr = '';

  child.stdout.on('data', (chunk) => {
    stdout += chunk.toString();
  });

  child.stderr.on('data', (chunk) => {
    stderr += chunk.toString();
  });

  const baseUrl = `http://127.0.0.1:${port}`;
  const deadline = Date.now() + 60_000;
  let lastError;

  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(
        `Dev server exited early with code ${child.exitCode}\n${stdout}\n${stderr}`.trim(),
      );
    }

    try {
      const response = await fetch(baseUrl);
      if (response.ok) {
        return {
          child,
          baseUrl,
          getLogs() {
            return { stdout, stderr };
          },
        };
      }
    } catch (error) {
      lastError = error;
    }

    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  child.kill('SIGTERM');
  throw new Error(`Timed out waiting for dev server at ${baseUrl}: ${lastError}`);
}

export async function stopDevServer(server) {
  if (!server?.child || server.child.exitCode !== null) {
    return;
  }

  server.child.kill('SIGTERM');
  await new Promise((resolve) => {
    server.child.once('exit', () => resolve());
    setTimeout(resolve, 5_000);
  });
}

export async function fetchHtml(server, pathname) {
  const response = await fetch(new URL(pathname, server.baseUrl));
  const html = await response.text();

  return {
    status: response.status,
    html,
  };
}
