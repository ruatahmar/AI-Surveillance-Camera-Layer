import { NextRequest, NextResponse } from "next/server";
import { parse, stringify } from "smol-toml";
import { readFileSync, writeFileSync } from "fs";
import { resolve } from "path";

function getConfigPath(): string {
  if (process.env.CONFIG_PATH) return resolve(process.env.CONFIG_PATH);
  return resolve(process.cwd(), "../config.toml");
}

function readConfig(): Record<string, unknown> {
  const path = getConfigPath();
  const raw = readFileSync(path, "utf-8");
  return parse(raw) as Record<string, unknown>;
}

function deepMerge(
  base: Record<string, unknown>,
  patch: Record<string, unknown>
): Record<string, unknown> {
  const result: Record<string, unknown> = { ...base };
  for (const key of Object.keys(patch)) {
    const baseVal = base[key];
    const patchVal = patch[key];
    if (
      patchVal !== null &&
      typeof patchVal === "object" &&
      !Array.isArray(patchVal) &&
      typeof baseVal === "object" &&
      baseVal !== null &&
      !Array.isArray(baseVal)
    ) {
      result[key] = deepMerge(
        baseVal as Record<string, unknown>,
        patchVal as Record<string, unknown>
      );
    } else {
      result[key] = patchVal;
    }
  }
  return result;
}

export async function GET() {
  try {
    const config = readConfig();
    return NextResponse.json(config);
  } catch (err) {
    console.error("Failed to read config:", err);
    return NextResponse.json(
      { error: "Failed to read config.toml", detail: String(err) },
      { status: 500 }
    );
  }
}

function mergeSources(
  current: Record<string, unknown>,
  patch: Record<string, unknown>
): Array<Record<string, unknown>> {
  const currentSources = (current.sources ?? []) as Array<Record<string, unknown>>;
  const patchSources = patch.sources as Array<Record<string, unknown>> | undefined;
  if (!patchSources) return currentSources;

  const sourceMap = new Map<string, Record<string, unknown>>();
  for (const src of currentSources) {
    sourceMap.set(src.name as string, { ...src });
  }
  for (const src of patchSources) {
    const name = src.name as string;
    if (sourceMap.has(name)) {
      // Only overwrite fields present in the patch source
      sourceMap.set(name, { ...sourceMap.get(name)!, ...src });
    } else {
      sourceMap.set(name, { ...src });
    }
  }
  return Array.from(sourceMap.values());
}

export async function PATCH(req: NextRequest) {
  try {
    const patch = await req.json();
    const current = readConfig();

    // Merge everything except sources (deepMerge replaces arrays)
    const { sources: _ps, ...restPatch } = patch;
    const { sources: _cs, ...restCurrent } = current;
    const merged = deepMerge(restCurrent, restPatch);
    merged.sources = mergeSources(current, patch);

    const toml = stringify(merged);
    writeFileSync(getConfigPath(), toml, "utf-8");
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("Failed to write config:", err);
    return NextResponse.json(
      { error: "Failed to write config.toml", detail: String(err) },
      { status: 500 }
    );
  }
}