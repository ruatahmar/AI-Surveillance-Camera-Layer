"use client";

import { useEffect, useState, useCallback } from "react";

type Alert = {
  id: string;
  timestamp: string;
  camera: string;
  frame: string;
  label: string;
};

type LoiteringWindow = {
  start: string;
  end: string;
};

type SourceConfig = {
  name: string;
  source: number | string;
  loitering_enabled: boolean;
  loitering_threshold: number | null;
  loitering_windows: LoiteringWindow[];
  loitering_alert_limit: number;
  alert_limit_per_track: number;
  alert_cooldown: number;
  no_id_alert_distance: number;
  alert_confirm_frames: number;
  process_every_n_frames: number;
  crowd_min_people: number;
  crowd_min_duration: number;
  green_lanyard_enabled: boolean;
  lanyard_green_threshold: number;
};

type GeneralConfig = {
  model_path: string;
  conf_threshold: number;
  loitering_threshold: number;
};

type Config = {
  general: GeneralConfig;
  sources: SourceConfig[];
};

export default function Dashboard() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [config, setConfig] = useState<Config | null>(null);
  const [editedConfig, setEditedConfig] = useState<Config | null>(null);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<string>("");
  const [configError, setConfigError] = useState<string>("");

  const fetchAlerts = async () => {
    try {
      const res = await fetch("/api/alerts");
      const data = await res.json();
      setAlerts(data.alerts);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (e) {
      console.error("failed to fetch alerts", e);
    }
  };

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch("/api/config");
      const data = await res.json();
      if (!res.ok || data.error) {
        setConfigError(`Failed to load config: ${data.error ?? "unknown error"}${data.detail ? ` — ${data.detail}` : ""}`);
        return;
      }
      setConfig(data);
      setEditedConfig(structuredClone(data));
      setConfigError("");
    } catch (e) {
      console.error("failed to fetch config", e);
      setConfigError("Failed to load config — is config.toml accessible?");
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (settingsOpen && !config) fetchConfig();
  }, [settingsOpen, config, fetchConfig]);

  const handleSave = async () => {
    if (!editedConfig) return;
    setSaving(true);
    try {
      const res = await fetch("/api/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editedConfig),
      });
      if (!res.ok) throw new Error("Save failed");
      setConfig(structuredClone(editedConfig));
      setLastSaved(new Date().toLocaleTimeString());
      setConfigError("");
    } catch (e) {
      console.error(e);
      setConfigError("Failed to save config.");
    } finally {
      setSaving(false);
    }
  };

  const updateGeneral = (field: keyof GeneralConfig, value: unknown) => {
    setEditedConfig((prev) =>
      prev ? { ...prev, general: { ...prev.general, [field]: value } } : prev
    );
  };

  const updateSource = (idx: number, field: keyof SourceConfig, value: unknown) => {
    setEditedConfig((prev) => {
      if (!prev) return prev;
      const sources = prev.sources.map((s, i) =>
        i === idx ? { ...s, [field]: value } : s
      );
      return { ...prev, sources };
    });
  };

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white font-mono p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-end justify-between mb-10 border-b border-white/10 pb-6">
          <div>
            <p className="text-xs text-white/30 tracking-widest uppercase mb-1">AI Surveillance</p>
            <h1 className="text-3xl font-bold tracking-tight">Alert Feed</h1>
          </div>
          <div className="flex items-end gap-6">
            <div className="text-right">
              <p className="text-xs text-white/30 mb-1">last updated</p>
              <p className="text-sm text-white/60">{lastUpdated || "—"}</p>
            </div>
            <button
              onClick={() => setSettingsOpen(true)}
              className="px-4 py-2 text-xs uppercase tracking-widest border border-white/10 rounded-lg hover:bg-white/5 transition-colors text-white/60 hover:text-white"
            >
              ⚙ Settings
            </button>
          </div>
        </div>

        <div className="flex gap-4 mb-8 flex-wrap">
          <StatPill label="Total Alerts" value={alerts.length} />
          <StatPill
            label="No ID"
            value={alerts.filter((a) => a.label === "no_id").length}
            accent="red"
          />
          <StatPill
            label="Loitering"
            value={alerts.filter((a) => a.label === "loitering").length}
            accent="red"
          />
          <StatPill
            label="Crowd"
            value={alerts.filter((a) => a.label === "crowd").length}
            accent="blue"
          />
          <StatPill
            label="Wrong Lanyard"
            value={alerts.filter((a) => a.label === "wrong_lanyard").length}
            accent="amber"
          />
          <StatPill
            label="Green Lanyard"
            value={alerts.filter((a) => a.label === "green_lanyard").length}
            accent="green"
          />
        </div>

        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 border border-white/10 rounded-xl text-white/20">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse mb-4" />
            <p className="text-sm tracking-widest uppercase">Monitoring — no alerts yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {alerts
              .slice()
              .reverse()
              .map((alert) => (
                <AlertCard key={alert.id} alert={alert} />
              ))}
          </div>
        )}
      </div>

      {settingsOpen && (
        <SettingsModal
          config={editedConfig}
          saving={saving}
          lastSaved={lastSaved}
          error={configError}
          onClose={() => setSettingsOpen(false)}
          onSave={handleSave}
          onUpdateGeneral={updateGeneral}
          onUpdateSource={updateSource}
        />
      )}
    </main>
  );
}

// ─── Stat Pill ────────────────────────────────────────────────────────────────

function StatPill({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: "red" | "green" | "blue" | "amber";
}) {
  const colors = {
    red: "text-red-400",
    green: "text-green-400",
    blue: "text-blue-400",
    amber: "text-amber-400",
  };
  return (
    <div className="flex-1 min-w-[120px] border border-white/10 rounded-lg px-4 py-3">
      <p className="text-xs text-white/30 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ? colors[accent] : "text-white"}`}>{value}</p>
    </div>
  );
}

// ─── Alert Card ───────────────────────────────────────────────────────────────

function AlertCard({ alert }: { alert: Alert }) {
  const labelStyles: Record<string, string> = {
    no_id: "bg-red-500/10 text-red-400 border-red-500/20",
    loitering: "bg-red-500/10 text-red-400 border-red-500/20",
    crowd: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    Cards: "bg-green-500/10 text-green-400 border-green-500/20",
    Lanyard: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    wrong_lanyard: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    green_lanyard: "bg-green-500/10 text-green-400 border-green-500/20",
    unknown: "bg-white/5 text-white/40 border-white/10",
  };

  const labelText: Record<string, string> = {
    no_id: "No ID",
    loitering: "Loitering",
    crowd: "Crowd",
    Cards: "Card Detected",
    Lanyard: "Lanyard Detected",
    wrong_lanyard: "Wrong Lanyard",
    green_lanyard: "Green Lanyard",
    unknown: "Unknown",
  };

  return (
    <div className="border border-white/10 rounded-xl overflow-hidden bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
      <div className="relative aspect-video bg-black">
        {alert.frame ? (
          <img
            src={`data:image/jpeg;base64,${alert.frame}`}
            alt="alert frame"
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-white/10 text-xs">
            no frame
          </div>
        )}
        <span
          className={`absolute top-2 right-2 text-xs px-2 py-1 rounded border font-mono uppercase tracking-wider ${
            labelStyles[alert.label] ?? labelStyles.unknown
          }`}
        >
          {labelText[alert.label] ?? alert.label}
        </span>
      </div>
      <div className="px-4 py-3 flex justify-between items-center">
        <p className="text-xs text-white/40 font-mono">{alert.camera}</p>
        <p className="text-xs text-white/25 font-mono">{alert.timestamp}</p>
      </div>
    </div>
  );
}

// ─── Settings Modal ───────────────────────────────────────────────────────────

function SettingsModal({
  config,
  saving,
  lastSaved,
  error,
  onClose,
  onSave,
  onUpdateGeneral,
  onUpdateSource,
}: {
  config: Config | null;
  saving: boolean;
  lastSaved: string;
  error: string;
  onClose: () => void;
  onSave: () => void;
  onUpdateGeneral: (field: keyof GeneralConfig, value: unknown) => void;
  onUpdateSource: (idx: number, field: keyof SourceConfig, value: unknown) => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-[#111] border border-white/10 rounded-2xl shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 sticky top-0 bg-[#111] z-10">
          <h2 className="text-sm font-bold uppercase tracking-widest text-white/80">Configuration</h2>
          <div className="flex items-center gap-4">
            {lastSaved && (
              <p className="text-xs text-white/30">saved {lastSaved}</p>
            )}
            {error && (
              <p className="text-xs text-red-400">{error}</p>
            )}
            <button
              onClick={onClose}
              className="text-white/30 hover:text-white text-lg leading-none"
            >
              ✕
            </button>
          </div>
        </div>

        {!config || !config.general ? (
          <div className="p-6 text-sm text-center">
            {error
              ? <p className="text-red-400">{error}</p>
              : <p className="text-white/30">Loading config…</p>
            }
          </div>
        ) : (
          <div className="p-6 space-y-8">
            {/* General Section */}
            <section>
              <h3 className="text-xs uppercase tracking-widest text-white/30 mb-4">General</h3>
              <div className="space-y-4">
                <SettingsField label="Model Path" requiresRestart>
                  <input
                    type="text"
                    value={config.general.model_path}
                    onChange={(e) => onUpdateGeneral("model_path", e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 focus:outline-none focus:border-white/30"
                  />
                </SettingsField>

                <SettingsField label="Confidence Threshold">
                  <SliderInput
                    value={config.general.conf_threshold}
                    min={0.1}
                    max={1.0}
                    step={0.05}
                    onChange={(v) => onUpdateGeneral("conf_threshold", v)}
                  />
                </SettingsField>

                <SettingsField label="Loitering Threshold (s)">
                  <SliderInput
                    value={config.general.loitering_threshold}
                    min={1}
                    max={120}
                    step={1}
                    onChange={(v) => onUpdateGeneral("loitering_threshold", v)}
                  />
                </SettingsField>
              </div>
            </section>

            {/* Per-source sections */}
            {config.sources.map((src, idx) => (
              <section key={src.name}>
                <h3 className="text-xs uppercase tracking-widest text-white/30 mb-4">
                  Source — {src.name}
                </h3>
                <div className="space-y-4">
                  <SettingsField label="Source (URL or index)" requiresRestart>
                    <input
                      type="text"
                      value={String(src.source)}
                      onChange={(e) => {
                        const v = e.target.value;
                        onUpdateSource(idx, "source", isNaN(Number(v)) ? v : Number(v));
                      }}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 focus:outline-none focus:border-white/30"
                    />
                  </SettingsField>

                  <SettingsField label="Loitering Enabled">
                    <Toggle
                      value={src.loitering_enabled}
                      onChange={(v) => onUpdateSource(idx, "loitering_enabled", v)}
                    />
                  </SettingsField>

                  <SettingsField label="Loitering Threshold Override (s)">
                    <SliderInput
                      value={src.loitering_threshold ?? 0}
                      min={0}
                      max={120}
                      step={1}
                      onChange={(v) => onUpdateSource(idx, "loitering_threshold", v === 0 ? null : v)}
                      nullLabel="Use global"
                    />
                  </SettingsField>

                  <SettingsField label="Loitering Alert Limit">
                    <NumberInput
                      value={src.loitering_alert_limit}
                      min={1}
                      onChange={(v) => onUpdateSource(idx, "loitering_alert_limit", v)}
                    />
                  </SettingsField>

                  <SettingsField label="Alert Limit per Track">
                    <NumberInput
                      value={src.alert_limit_per_track}
                      min={1}
                      onChange={(v) => onUpdateSource(idx, "alert_limit_per_track", v)}
                    />
                  </SettingsField>

                  <SettingsField label="Alert Cooldown (s)">
                    <SliderInput
                      value={src.alert_cooldown}
                      min={5}
                      max={300}
                      step={5}
                      onChange={(v) => onUpdateSource(idx, "alert_cooldown", v)}
                    />
                  </SettingsField>

                  <SettingsField label="No-ID Alert Distance (px)">
                    <SliderInput
                      value={src.no_id_alert_distance}
                      min={10}
                      max={500}
                      step={10}
                      onChange={(v) => onUpdateSource(idx, "no_id_alert_distance", v)}
                    />
                  </SettingsField>

                  <SettingsField label="Alert Confirm Frames">
                    <NumberInput
                      value={src.alert_confirm_frames}
                      min={1}
                      onChange={(v) => onUpdateSource(idx, "alert_confirm_frames", v)}
                    />
                  </SettingsField>

                  <SettingsField label="Process Every N Frames">
                    <NumberInput
                      value={src.process_every_n_frames}
                      min={1}
                      onChange={(v) => onUpdateSource(idx, "process_every_n_frames", v)}
                    />
                  </SettingsField>

                  <SettingsField label="Crowd Min People">
                    <NumberInput
                      value={src.crowd_min_people}
                      min={2}
                      onChange={(v) => onUpdateSource(idx, "crowd_min_people", v)}
                    />
                  </SettingsField>

                  <SettingsField label="Crowd Min Duration (s)">
                    <SliderInput
                      value={src.crowd_min_duration}
                      min={1}
                      max={120}
                      step={1}
                      onChange={(v) => onUpdateSource(idx, "crowd_min_duration", v)}
                    />
                  </SettingsField>

                  <SettingsField label="Green Lanyard Enabled">
                    <Toggle
                      value={src.green_lanyard_enabled}
                      onChange={(v) => onUpdateSource(idx, "green_lanyard_enabled", v)}
                    />
                  </SettingsField>

                  <SettingsField label="Lanyard Green Threshold">
                    <SliderInput
                      value={src.lanyard_green_threshold}
                      min={0.01}
                      max={0.5}
                      step={0.01}
                      onChange={(v) => onUpdateSource(idx, "lanyard_green_threshold", v)}
                    />
                  </SettingsField>
                </div>
              </section>
            ))}
          </div>
        )}

        <div className="sticky bottom-0 bg-[#111] border-t border-white/10 px-6 py-4 flex justify-end">
          <button
            onClick={onSave}
            disabled={saving || !config}
            className="px-6 py-2 text-xs uppercase tracking-widest bg-white text-black rounded-lg font-bold hover:bg-white/90 disabled:opacity-40 transition-colors"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Settings sub-components ──────────────────────────────────────────────────

function SettingsField({
  label,
  requiresRestart,
  children,
}: {
  label: string;
  requiresRestart?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-2 gap-4 items-center">
      <div>
        <p className="text-xs text-white/60">{label}</p>
        {requiresRestart && (
          <p className="text-xs text-amber-400/60 mt-0.5">⚠ requires restart</p>
        )}
      </div>
      <div>{children}</div>
    </div>
  );
}

function SliderInput({
  value,
  min,
  max,
  step,
  onChange,
  nullLabel,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  nullLabel?: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="flex-1 accent-white"
      />
      <span className="text-xs text-white/50 w-12 text-right tabular-nums">
        {nullLabel && value === min ? nullLabel : value}
      </span>
    </div>
  );
}

function NumberInput({
  value,
  min,
  onChange,
}: {
  value: number;
  min: number;
  onChange: (v: number) => void;
}) {
  return (
    <input
      type="number"
      min={min}
      value={value}
      onChange={(e) => onChange(parseInt(e.target.value, 10))}
      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 focus:outline-none focus:border-white/30"
    />
  );
}

function Toggle({
  value,
  onChange,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      onClick={() => onChange(!value)}
      className={`relative w-10 h-6 rounded-full transition-colors ${
        value ? "bg-white" : "bg-white/10"
      }`}
    >
      <span
        className={`absolute top-1 w-4 h-4 rounded-full transition-transform ${
          value ? "translate-x-5 bg-black" : "translate-x-1 bg-white/40"
        }`}
      />
    </button>
  );
}