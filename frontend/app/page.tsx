"use client";

import { useEffect, useState } from "react";

type Alert = {
  id: string;
  timestamp: string;
  camera: string;
  frame: string;
  label: string;
};

export default function Dashboard() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");

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

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-white font-mono p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-end justify-between mb-10 border-b border-white/10 pb-6">
          <div>
            <p className="text-xs text-white/30 tracking-widest uppercase mb-1">AI Surveillance</p>
            <h1 className="text-3xl font-bold tracking-tight">Alert Feed</h1>
          </div>
          <div className="text-right">
            <p className="text-xs text-white/30 mb-1">last updated</p>
            <p className="text-sm text-white/60">{lastUpdated || "—"}</p>
          </div>
        </div>

        <div className="flex gap-4 mb-8">
          <StatPill label="Total Alerts" value={alerts.length} />
          <StatPill
            label="No ID"
            value={alerts.filter((a) => a.label === "no_id").length}
            accent="red"
          />
          <StatPill
            label="Students"
            value={alerts.filter((a) => a.label === "student").length}
            accent="green"
          />
          <StatPill
            label="Teachers"
            value={alerts.filter((a) => a.label === "teacher").length}
            accent="blue"
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
    </main>
  );
}

function StatPill({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: "red" | "green" | "blue";
}) {
  const colors = {
    red: "text-red-400",
    green: "text-green-400",
    blue: "text-blue-400",
  };
  return (
    <div className="flex-1 border border-white/10 rounded-lg px-4 py-3">
      <p className="text-xs text-white/30 uppercase tracking-widest mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ? colors[accent] : "text-white"}`}>{value}</p>
    </div>
  );
}

function AlertCard({ alert }: { alert: Alert }) {
  const labelStyles: Record<string, string> = {
    no_id: "bg-red-500/10 text-red-400 border-red-500/20",
    student: "bg-green-500/10 text-green-400 border-green-500/20",
    teacher: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    unknown: "bg-white/5 text-white/40 border-white/10",
  };

  const labelText: Record<string, string> = {
    no_id: "No ID",
    student: "Student",
    teacher: "Teacher",
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
          className={`absolute top-2 right-2 text-xs px-2 py-1 rounded border font-mono uppercase tracking-wider ${labelStyles[alert.label] ?? labelStyles.unknown
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