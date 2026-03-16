"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const data = [
  { time: "00:00", events: 320 },
  { time: "02:00", events: 180 },
  { time: "04:00", events: 140 },
  { time: "06:00", events: 280 },
  { time: "08:00", events: 520 },
  { time: "10:00", events: 780 },
  { time: "12:00", events: 920 },
  { time: "14:00", events: 860 },
  { time: "16:00", events: 1040 },
  { time: "18:00", events: 880 },
  { time: "20:00", events: 640 },
  { time: "22:00", events: 420 },
];

export function EventVolumeChart() {
  return (
    <div className="card card-hover">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">Event Volume</h3>
      <p className="text-xs text-gray-500 mb-4">Last 24 hours</p>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="tealGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0d9488" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#0d9488" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#fff",
                border: "1px solid #e2e8f0",
                borderRadius: "8px",
                fontSize: "12px",
                boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)",
              }}
            />
            <Area
              type="monotone"
              dataKey="events"
              stroke="#0d9488"
              strokeWidth={2}
              fill="url(#tealGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
