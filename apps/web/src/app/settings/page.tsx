import { Shield, Database, Cpu, Key, Bell, Palette } from "lucide-react";

const sections = [
  {
    title: "Tenant Configuration",
    icon: Shield,
    settings: [
      { label: "Organization Name", value: "Acme Logistics", type: "text" },
      { label: "Plan Tier", value: "Professional", type: "badge" },
      { label: "Tenant ID", value: "a1b2c3d4-e5f6-7890-abcd-ef1234567890", type: "mono" },
    ],
  },
  {
    title: "API & Rate Limits",
    icon: Key,
    settings: [
      { label: "API Version", value: "v1", type: "text" },
      { label: "Rate Limit", value: "300 requests/min", type: "text" },
      { label: "AI Query Limit", value: "300 requests/min", type: "text" },
      { label: "API Key", value: "oie_live_••••••••••••3kF9", type: "mono" },
    ],
  },
  {
    title: "AI Configuration",
    icon: Cpu,
    settings: [
      { label: "Default Model", value: "Claude Sonnet", type: "text" },
      { label: "Max Context Tokens", value: "128,000", type: "text" },
      { label: "Prompt Evaluation Threshold", value: "80%", type: "text" },
      { label: "Policy Guards", value: "Enabled", type: "badge-green" },
    ],
  },
  {
    title: "Database",
    icon: Database,
    settings: [
      { label: "Row-Level Security", value: "Enforced", type: "badge-green" },
      { label: "Connection Pool", value: "28 / 100", type: "text" },
      { label: "Migrations", value: "Up to date", type: "badge-green" },
      { label: "Vector Extension", value: "pgvector enabled", type: "text" },
    ],
  },
  {
    title: "Notifications",
    icon: Bell,
    settings: [
      { label: "Critical Alerts", value: "Email + Slack", type: "text" },
      { label: "High Alerts", value: "Slack", type: "text" },
      { label: "Medium Alerts", value: "Dashboard only", type: "text" },
      { label: "Low Alerts", value: "Dashboard only", type: "text" },
    ],
  },
  {
    title: "Appearance",
    icon: Palette,
    settings: [
      { label: "Theme", value: "System default", type: "text" },
      { label: "Dashboard Refresh", value: "30 seconds", type: "text" },
      { label: "Timezone", value: "America/New_York (EDT)", type: "text" },
    ],
  },
];

function SettingValue({ value, type }: { value: string; type: string }) {
  if (type === "mono") {
    return <span className="text-sm font-mono text-gray-600 bg-gray-50 px-2 py-1 rounded">{value}</span>;
  }
  if (type === "badge") {
    return <span className="text-xs font-medium bg-teal-50 text-teal-700 px-2.5 py-1 rounded-md">{value}</span>;
  }
  if (type === "badge-green") {
    return <span className="text-xs font-medium bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-md">{value}</span>;
  }
  return <span className="text-sm text-gray-700">{value}</span>;
}

export default function SettingsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Settings</h2>
        <p className="text-sm text-gray-500 mt-1">
          Platform configuration and preferences
        </p>
      </div>

      <div className="space-y-6">
        {sections.map((section) => {
          const Icon = section.icon;
          return (
            <div key={section.title} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100">
                <Icon className="w-4 h-4 text-teal-600" />
                <h3 className="text-sm font-semibold text-gray-900">{section.title}</h3>
              </div>
              <div className="divide-y divide-gray-50">
                {section.settings.map((setting) => (
                  <div key={setting.label} className="flex items-center justify-between px-6 py-4">
                    <span className="text-sm text-gray-500">{setting.label}</span>
                    <SettingValue value={setting.value} type={setting.type} />
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
