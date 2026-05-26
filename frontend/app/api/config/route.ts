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

export async function PATCH(req: NextRequest) {
  try {
    const patch = await req.json();
    const current = readConfig();
    const merged = deepMerge(current, patch);
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