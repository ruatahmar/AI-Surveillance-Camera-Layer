import { NextRequest, NextResponse } from "next/server";

type Alert = {
    id: string;
    timestamp: string;
    camera: string;
    frame: string;
    label: string;
};

const alerts: Alert[] = [];

export async function GET() {
    return NextResponse.json({ alerts });
}

export async function POST(req: NextRequest) {
    const body = await req.json();

    const alert: Alert = {
        id: crypto.randomUUID(),
        timestamp: new Date().toLocaleString(),
        camera: body.camera ?? "unknown",
        frame: body.frame ?? "",
        label: body.label ?? "unknown",
    };

    alerts.push(alert);

    // keeping the last 50 alerts only
    if (alerts.length > 50) alerts.shift();

    return NextResponse.json({ ok: true, id: alert.id });
}