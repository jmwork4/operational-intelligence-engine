"use client";

import { useState } from "react";
import { BookOpen, Play, Clock, Shield, FileText, AlertTriangle, BarChart3 } from "lucide-react";

const playbooks = [
  {
    id: "incident",
    name: "Incident Response",
    description:
      "Auto-generate relevant docs, similar past incidents, remediation steps, and a draft customer notification when a critical alert fires.",
    icon: Shield,
    lastRun: "12 min ago",
    color: "text-red-500",
    bg: "bg-red-50",
  },
  {
    id: "handoff",
    name: "Shift Handoff",
    description:
      "Summarise all events, alerts, and actions from the last shift. Highlight unresolved items for the incoming team.",
    icon: Clock,
    lastRun: "6 hr ago",
    color: "text-blue-500",
    bg: "bg-blue-50",
  },
  {
    id: "digest",
    name: "Weekly Digest",
    description:
      "Top incidents, trend analysis (improving vs worsening metrics), and actionable recommendations for the week.",
    icon: BarChart3,
    lastRun: "3 days ago",
    color: "text-emerald-500",
    bg: "bg-emerald-50",
  },
  {
    id: "whatif",
    name: "What-If Analysis",
    description:
      "Model the downstream impact of operational changes — estimate alert volume shifts and SLA compliance effects.",
    icon: AlertTriangle,
    lastRun: "1 day ago",
    color: "text-amber-500",
    bg: "bg-amber-50",
  },
];

const mockIncidentResult = {
  alert_summary:
    "[CRITICAL] Late Shipment Alert on shipment SHP-2024-089: Shipment delayed 45 min on I-95, vendor priority high",
  similar_incidents: [
    { id: "ALR-412", rule: "Late Shipment Alert", entity: "SHP-2024-052", time: "3 days ago", status: "resolved" },
    { id: "ALR-398", rule: "Late Shipment Alert", entity: "SHP-2024-041", time: "5 days ago", status: "resolved" },
    { id: "ALR-387", rule: "Late Shipment Alert", entity: "SHP-2024-033", time: "1 week ago", status: "resolved" },
  ],
  relevant_docs: [
    { title: "Shipment Delay Escalation SOP", type: "procedure" },
    { title: "Carrier SLA Agreement — FastFreight", type: "contract" },
    { title: "Customer Communication Templates", type: "template" },
  ],
  remediation_steps: [
    "1. Acknowledge alert and assess current status of SHP-2024-089",
    "2. Review Late Shipment Alert threshold configuration",
    "3. Check for correlated events in the last 30 minutes",
    "4. Reference resolution of similar incident ALR-412 for guidance",
    "5. Update alert status and document resolution",
  ],
  draft_notification:
    "Subject: [CRITICAL] Operational Alert — SHP-2024-089\n\nDear Team,\n\nAn operational alert has been triggered:\n\n  Alert: Late Shipment Alert\n  Severity: CRITICAL\n  Entity: SHP-2024-089\n  Details: Shipment delayed 45 min on I-95\n\nOur team is actively investigating. We will provide an update within 30 minutes.\n\n— OIE Operations Team",
};

export default function PlaybooksPage() {
  const [activePlaybook, setActivePlaybook] = useState<string | null>("incident");
  const [running, setRunning] = useState<string | null>(null);

  const handleRun = (id: string) => {
    setRunning(id);
    setTimeout(() => {
      setRunning(null);
      setActivePlaybook(id);
    }, 1500);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900">AI Playbooks</h2>
        <p className="text-sm text-gray-500 mt-1">
          Automated intelligence workflows that run when you need them most
        </p>
      </div>

      {/* Playbook cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {playbooks.map((pb) => {
          const Icon = pb.icon;
          const isActive = activePlaybook === pb.id;
          return (
            <div
              key={pb.id}
              className={`bg-white rounded-xl border-2 p-5 transition-all cursor-pointer ${
                isActive ? "border-teal-500 shadow-md" : "border-gray-100 hover:border-gray-200"
              }`}
              onClick={() => setActivePlaybook(pb.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg ${pb.bg} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${pb.color}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{pb.name}</h3>
                    <p className="text-xs text-gray-400 mt-0.5">Last run: {pb.lastRun}</p>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRun(pb.id);
                  }}
                  disabled={running === pb.id}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    running === pb.id
                      ? "bg-gray-100 text-gray-400 cursor-wait"
                      : "bg-teal-600 text-white hover:bg-teal-700"
                  }`}
                >
                  <Play className="w-3.5 h-3.5" />
                  {running === pb.id ? "Running..." : "Run"}
                </button>
              </div>
              <p className="text-sm text-gray-500 mt-3">{pb.description}</p>
            </div>
          );
        })}
      </div>

      {/* Results panel */}
      {activePlaybook === "incident" && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
          <div className="px-6 py-4 border-b border-gray-100">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-red-500" />
              <h3 className="font-semibold text-gray-900">Incident Response — Sample Output</h3>
            </div>
          </div>
          <div className="p-6 space-y-6">
            {/* Alert summary */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Alert Summary</h4>
              <div className="bg-red-50 border border-red-100 rounded-lg p-3">
                <p className="text-sm text-red-800">{mockIncidentResult.alert_summary}</p>
              </div>
            </div>

            {/* Remediation steps */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Remediation Steps</h4>
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                {mockIncidentResult.remediation_steps.map((step, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <div className="w-5 h-5 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-bold">{i + 1}</span>
                    </div>
                    <p className="text-sm text-gray-700">{step.replace(/^\d+\.\s*/, "")}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Similar incidents */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Similar Past Incidents</h4>
                <div className="space-y-2">
                  {mockIncidentResult.similar_incidents.map((inc) => (
                    <div key={inc.id} className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                      <div>
                        <span className="text-sm font-medium text-gray-800">{inc.id}</span>
                        <span className="text-xs text-gray-400 ml-2">{inc.entity}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">{inc.time}</span>
                        <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-100 text-emerald-700">
                          {inc.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Relevant docs */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Relevant Documents</h4>
                <div className="space-y-2">
                  {mockIncidentResult.relevant_docs.map((doc, i) => (
                    <div key={i} className="flex items-center gap-3 bg-gray-50 rounded-lg p-3">
                      <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-gray-800">{doc.title}</p>
                        <p className="text-xs text-gray-400">{doc.type}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Draft notification */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Draft Customer Notification</h4>
              <pre className="bg-navy-900 text-gray-300 rounded-lg p-4 text-xs leading-relaxed whitespace-pre-wrap font-mono">
                {mockIncidentResult.draft_notification}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
