#!/usr/bin/env node

import { access, mkdir } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { spawn, spawnSync } from "node:child_process";

const packageName = "@nutrient-sdk/dws-mcp-server";
const packageVersion = "0.1.2";
const cacheBase =
  process.env.NUTRIENT_DWS_MCP_CACHE_DIR ||
  process.env.XDG_CACHE_HOME ||
  (process.platform === "win32" && process.env.LOCALAPPDATA) ||
  join(homedir(), ".cache");
const installRoot = join(cacheBase, "nutrient-dws-mcp", packageVersion);
const serverEntry = join(
  installRoot,
  "node_modules",
  "@nutrient-sdk",
  "dws-mcp-server",
  "dist",
  "index.js",
);

async function ensureServerInstalled() {
  try {
    await access(serverEntry);
    return;
  } catch {
    await mkdir(installRoot, { recursive: true });
  }

  const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";
  const result = spawnSync(
    npmCommand,
    [
      "install",
      "--prefix",
      installRoot,
      "--no-save",
      "--ignore-scripts",
      "--no-audit",
      "--no-fund",
      "--loglevel=error",
      `${packageName}@${packageVersion}`,
    ],
    {
      stdio: ["ignore", "ignore", "inherit"],
      env: { ...process.env, npm_config_update_notifier: "false" },
    },
  );

  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`npm install exited with status ${result.status ?? "unknown"}`);
  }

  await access(serverEntry);
}

try {
  await ensureServerInstalled();
} catch (error) {
  console.error(`Unable to prepare ${packageName}: ${error instanceof Error ? error.message : error}`);
  process.exit(1);
}

const server = spawn(process.execPath, [serverEntry], {
  stdio: "inherit",
  env: process.env,
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.kill(signal));
}

server.on("error", (error) => {
  console.error(`Unable to start ${packageName}: ${error.message}`);
  process.exitCode = 1;
});

server.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exitCode = code ?? 1;
});
