"use client";

import { useState } from "react";
import {
  Workflow,
  Bell,
  Phone,
  Mail,
  Clock,
  Sparkles,
  Globe,
  UserCheck,
  ChevronRight,
  Plus,
  Copy,
  ToggleLeft,
  ToggleRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";

const stepIcons: Record<string, any> = {
  notify: Bell,
  api_call: Globe,
  approve: UserCheck,
  delay: Clock,
  ai_analyze: Sparkles,
};

const channelIcons: Record<string, any> = {
  slack: Bell,
  pagerduty: Phone,
  email: Mail,
};

interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  trigger: string;
  steps: { type: string; label: string; detail: string }[];
}

const templates: WorkflowTemplate[] = [
  {
    id: "critical-alert",
    name: "Critical Alert Escalation",
    description: "Notify Slack and PagerDuty, then escalate to manager via email if not acknowledged in 15 minutes.",
    trigger: "Alert severity = critical",
    steps: [
      { type: "notify", label: "Slack #ops-critical", detail: "Post alert details to critical ops channel" },
      { type: "notify", label: "PagerDuty on-call", detail: "Page the on-call engineer" },
      { type: "delay", label: "Wait 15 min", detail: "Allow time for acknowledgement" },
      { type: "notify", label: "Email manager", detail: "Escalate unacknowledged alert to ops manager" },
    ],
  },
  {
    id: "sla-breach",
    name: "SLA Breach Response",
    description: "Run AI analysis, notify customer success, create ticket, and alert ops team.",
    trigger: "Event type = delivery_sla_breach",
    steps: [
      { type: "ai_analyze", label: "AI Analysis", detail: "Analyse breach cause and impact" },
      { type: "notify", label: "Email customer success", detail: "Alert customer-facing team" },
      { type: "api_call", label: "Create ticket", detail: "Open support ticket automatically" },
      { type: "notify", label: "Slack #ops-sla", detail: "Notify operations team" },
    ],
  },
  {
    id: "maintenance-due",
    name: "Maintenance Due Workflow",
    description: "Create maintenance ticket, notify fleet manager, wait 24h, then check status.",
    trigger: "Event type = maintenance_due",
    steps: [
      { type: "api_call", label: "Create ticket", detail: "Open maintenance work order" },
      { type: "notify", label: "Email fleet manager", detail: "Notify responsible manager" },
      { type: "delay", label: "Wait 24h", detail: "Allow scheduling time" },
      { type: "api_call", label: "Check status", detail: "Verify ticket has been addressed" },
    ],
  },
];

const configuredWorkflows = [
  { id: "wf-001", name: "Critical Alert Escalation", template: "critical-alert", enabled: true, lastRun: "12 min ago", runs: 47 },
  { id: "wf-002", name: "SLA Breach Response", template: "sla-breach", enabled: true, lastRun: "2 hr ago", runs: 23 },
  { id: "wf-003", name: "Maintenance Due Workflow", template: "maintenance-due", enabled: false, lastRun: "3 days ago", runs: 8 },
];

const recentExecutions = [
  { id: "exec-001", workflow: "Critical Alert Escalation", trigger: "ALR-482 (critical)", status: "completed", steps: "4/4", time: "12 min ago", duration: "15m 32s" },
  { id: "exec-002", workflow: "SLA Breach Response", trigger: "ALR-478 (high)", status: "completed", steps: "4/4", time: "2 hr ago", duration: "8.4s" },
  { id: "exec-003", workflow: "Critical Alert Escalation", trigger: "ALR-475 (critical)", status: "completed", steps: "3/4", time: "5 hr ago", duration: "15m 12s" },
  { id: "exec-004", workflow: "SLA Breach Response", trigger: "ALR-470 (high)", status: "failed", steps: "2/4", time: "1 day ago", duration: "3.2s" },
  { id: "exec-005", workflow: "Maintenance Due Workflow", trigger: "VEH-078", status: "completed", steps: "4/4", time: "3 days ago", duration: "24h 5m" },
];

const statusStyles: Record<string, { icon: any; color: string; bg: string }> = {
  completed: { icon: CheckCircle2, color: "text-emerald-700", bg: "bg-emerald-50" },
  failed: { icon: XCircle, color: "text-red-700", bg: "bg-red-50" },
  running: { icon: AlertTriangle, color: "text-amber-700", bg: "bg-amber-50" },
};

export default function WorkflowsPage() {
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Workflow Automation</h2>
          <p className="text-sm text-gray-500 mt-1">
            Automate multi-step responses to alerts and events
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 transition-colors">
          <Plus className="w-4 h-4" />
          Create Workflow
        </button>
      </div>

      {/* Configured workflows */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Active Workflows</h3>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm divide-y divide-gray-50">
          {configuredWorkflows.map((wf) => (
            <div key={wf.id} className="flex items-center justify-between px-5 py-4">
              <div className="flex items-center gap-4">
                <div className="w-9 h-9 rounded-lg bg-teal-50 flex items-center justify-center">
                  <Workflow className="w-4.5 h-4.5 text-teal-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">{wf.name}</p>
                  <p className="text-xs text-gray-400">
                    {wf.runs} runs &middot; Last: {wf.lastRun}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span
                  className={`text-xs font-medium px-2 py-1 rounded-full ${
                    wf.enabled ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {wf.enabled ? "Enabled" : "Disabled"}
                </span>
                {wf.enabled ? (
                  <ToggleRight className="w-6 h-6 text-teal-600" />
                ) : (
                  <ToggleLeft className="w-6 h-6 text-gray-300" />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Templates */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Workflow Templates</h3>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {templates.map((t) => {
            const isSelected = selectedTemplate === t.id;
            return (
              <div
                key={t.id}
                className={`bg-white rounded-xl border-2 p-5 transition-all cursor-pointer ${
                  isSelected ? "border-teal-500 shadow-md" : "border-gray-100 hover:border-gray-200"
                }`}
                onClick={() => setSelectedTemplate(isSelected ? null : t.id)}
              >
                <h4 className="font-semibold text-gray-900 text-sm">{t.name}</h4>
                <p className="text-xs text-gray-500 mt-1">{t.description}</p>
                <div className="mt-3 mb-3">
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-md font-mono">
                    {t.trigger}
                  </span>
                </div>

                {/* Step visualization */}
                <div className="space-y-0">
                  {t.steps.map((step, i) => {
                    const StepIcon = stepIcons[step.type] || Bell;
                    return (
                      <div key={i}>
                        <div className="flex items-center gap-2.5 py-1.5">
                          <div className="w-7 h-7 rounded-md bg-gray-50 flex items-center justify-center flex-shrink-0">
                            <StepIcon className="w-3.5 h-3.5 text-gray-500" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-gray-800 truncate">{step.label}</p>
                          </div>
                        </div>
                        {i < t.steps.length - 1 && (
                          <div className="ml-3.5 h-3 border-l-2 border-dashed border-gray-200" />
                        )}
                      </div>
                    );
                  })}
                </div>

                <button className="mt-3 flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-100 transition-colors w-full justify-center">
                  <Copy className="w-3.5 h-3.5" />
                  Use Template
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Execution log */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Recent Executions</h3>
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
                <th className="text-left px-5 py-3 font-medium">Workflow</th>
                <th className="text-left px-5 py-3 font-medium">Trigger</th>
                <th className="text-left px-5 py-3 font-medium">Status</th>
                <th className="text-left px-5 py-3 font-medium">Steps</th>
                <th className="text-left px-5 py-3 font-medium">Duration</th>
                <th className="text-left px-5 py-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {recentExecutions.map((exec) => {
                const st = statusStyles[exec.status] || statusStyles.running;
                const StatusIcon = st.icon;
                return (
                  <tr key={exec.id} className="hover:bg-gray-50/50">
                    <td className="px-5 py-3 text-sm font-medium text-gray-900">{exec.workflow}</td>
                    <td className="px-5 py-3 text-sm text-gray-600 font-mono text-xs">{exec.trigger}</td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${st.bg} ${st.color}`}>
                        <StatusIcon className="w-3 h-3" />
                        {exec.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-sm text-gray-600">{exec.steps}</td>
                    <td className="px-5 py-3 text-sm text-gray-500 font-mono text-xs">{exec.duration}</td>
                    <td className="px-5 py-3 text-xs text-gray-400">{exec.time}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
