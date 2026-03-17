"use client";

import { useState } from "react";
import { Plus, Copy, Trash2, Key } from "lucide-react";

interface ApiKey {
  id: string;
  name: string;
  key: string;
  maskedKey: string;
  created: string;
  lastUsed: string;
  status: "Active" | "Revoked";
}

const mockKeys: ApiKey[] = [
  {
    id: "1",
    name: "Production Integration",
    key: "oie_prod_a1b2c3d4e5f6g7h8",
    maskedKey: "oie_prod_****g7h8",
    created: "Jan 15, 2026",
    lastUsed: "2 hours ago",
    status: "Active",
  },
  {
    id: "2",
    name: "Staging Environment",
    key: "oie_stg_x9y8z7w6v5u4t3s2",
    maskedKey: "oie_stg_****t3s2",
    created: "Feb 3, 2026",
    lastUsed: "Yesterday",
    status: "Active",
  },
  {
    id: "3",
    name: "CI/CD Pipeline",
    key: "oie_ci_m1n2o3p4q5r6s7t8",
    maskedKey: "oie_ci_****s7t8",
    created: "Feb 20, 2026",
    lastUsed: "5 days ago",
    status: "Active",
  },
  {
    id: "4",
    name: "Legacy Webhook (deprecated)",
    key: "oie_old_j1k2l3m4n5o6p7q8",
    maskedKey: "oie_old_****p7q8",
    created: "Nov 10, 2025",
    lastUsed: "3 weeks ago",
    status: "Revoked",
  },
];

export default function ApiKeysPage() {
  const [showGenerate, setShowGenerate] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (key: ApiKey) => {
    navigator.clipboard.writeText(key.key);
    setCopiedId(key.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">API Keys</h2>
          <p className="text-sm text-gray-500 mt-1">
            Manage API keys for external integrations
          </p>
        </div>
        <button
          onClick={() => setShowGenerate(!showGenerate)}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Generate New Key
        </button>
      </div>

      {/* Generate form */}
      {showGenerate && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Generate New API Key</h3>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Key name</label>
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="e.g., Production Integration"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
            </div>
            <button className="px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition-colors">
              Generate
            </button>
            <button
              onClick={() => setShowGenerate(false)}
              className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* API Keys table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Name</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Key</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Created</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Last Used</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Status</th>
              <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {mockKeys.map((apiKey) => (
              <tr key={apiKey.id} className="hover:bg-gray-50/50 transition-colors">
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <Key className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900">{apiKey.name}</span>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <code className="text-sm text-gray-600 font-mono bg-gray-50 px-2 py-0.5 rounded">
                    {apiKey.maskedKey}
                  </code>
                </td>
                <td className="px-5 py-3.5">
                  <span className="text-sm text-gray-500">{apiKey.created}</span>
                </td>
                <td className="px-5 py-3.5">
                  <span className="text-sm text-gray-500">{apiKey.lastUsed}</span>
                </td>
                <td className="px-5 py-3.5">
                  <span
                    className={`inline-flex px-2.5 py-0.5 text-xs font-medium rounded-full ${
                      apiKey.status === "Active"
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-red-50 text-red-700"
                    }`}
                  >
                    {apiKey.status}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => handleCopy(apiKey)}
                      className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors"
                      title="Copy key"
                    >
                      <Copy className="w-4 h-4" />
                      {copiedId === apiKey.id && (
                        <span className="absolute -mt-8 -ml-4 text-xs text-teal-600 bg-teal-50 px-2 py-0.5 rounded">
                          Copied!
                        </span>
                      )}
                    </button>
                    {apiKey.status === "Active" && (
                      <button
                        className="p-1.5 text-red-400 hover:text-red-600 transition-colors"
                        title="Revoke key"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Info box */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <p className="text-sm text-amber-800">
          <span className="font-medium">Security note:</span> API keys grant full access to your tenant data.
          Store them securely and rotate regularly. Revoked keys cannot be reactivated.
        </p>
      </div>
    </div>
  );
}
