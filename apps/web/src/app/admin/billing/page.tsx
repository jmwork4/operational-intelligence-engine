"use client";

import { Check, ArrowUpRight } from "lucide-react";

const plans = [
  {
    name: "Starter",
    price: "$49",
    period: "/mo",
    description: "For small teams getting started",
    features: [
      "10,000 events/month",
      "100 AI queries/month",
      "5 GB storage",
      "3 team members",
      "Email support",
      "7-day retention",
    ],
    current: false,
    cta: "Downgrade",
  },
  {
    name: "Professional",
    price: "$200",
    period: "/mo",
    description: "For growing operations teams",
    features: [
      "100,000 events/month",
      "5,000 AI queries/month",
      "50 GB storage",
      "15 team members",
      "Priority support",
      "90-day retention",
      "Custom rules",
      "Webhook integrations",
    ],
    current: true,
    cta: "Current Plan",
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For large-scale deployments",
    features: [
      "Unlimited events",
      "Unlimited AI queries",
      "Unlimited storage",
      "Unlimited team members",
      "Dedicated support",
      "365-day retention",
      "Custom rules",
      "Webhook integrations",
      "SSO / SAML",
      "Dedicated infrastructure",
      "SLA guarantees",
    ],
    current: false,
    cta: "Contact Sales",
  },
];

const usageBreakdown = [
  { label: "Events", used: 45230, limit: 100000, unit: "" },
  { label: "AI Queries", used: 1847, limit: 5000, unit: "" },
  { label: "Storage", used: 12.4, limit: 50, unit: "GB" },
  { label: "Team Members", used: 8, limit: 15, unit: "" },
];

const invoiceHistory = [
  { id: "INV-2026-003", date: "Mar 1, 2026", amount: "$200.00", status: "Paid" },
  { id: "INV-2026-002", date: "Feb 1, 2026", amount: "$200.00", status: "Paid" },
  { id: "INV-2026-001", date: "Jan 1, 2026", amount: "$200.00", status: "Paid" },
];

export default function BillingPage() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Page heading */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Billing & Plans</h2>
        <p className="text-sm text-gray-500 mt-1">
          Manage your subscription and view usage
        </p>
      </div>

      {/* Current plan card */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-gray-900">
              Professional Plan
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              $200/month, billed monthly. Next invoice on April 1, 2026.
            </p>
          </div>
          <span className="px-3 py-1.5 text-sm font-medium bg-teal-50 text-teal-700 rounded-full">
            Active
          </span>
        </div>
      </div>

      {/* Usage breakdown */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4">Usage This Month</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {usageBreakdown.map((item) => {
            const pct = (item.used / item.limit) * 100;
            const barColor = pct > 90 ? "bg-red-500" : pct > 70 ? "bg-amber-500" : "bg-teal-500";
            return (
              <div key={item.label}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-gray-700">{item.label}</span>
                  <span className="text-sm text-gray-500">
                    {item.used.toLocaleString()}{item.unit ? ` ${item.unit}` : ""} / {item.limit.toLocaleString()}{item.unit ? ` ${item.unit}` : ""}
                  </span>
                </div>
                <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${barColor} transition-all`}
                    style={{ width: `${Math.min(pct, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-1">{pct.toFixed(1)}% used</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Plan comparison */}
      <div>
        <h3 className="text-base font-semibold text-gray-900 mb-4">Compare Plans</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`bg-white rounded-xl border p-6 ${
                plan.current
                  ? "border-teal-300 ring-2 ring-teal-100"
                  : "border-gray-200"
              }`}
            >
              {plan.current && (
                <span className="inline-block px-2.5 py-0.5 text-xs font-medium bg-teal-50 text-teal-700 rounded-full mb-3">
                  Current Plan
                </span>
              )}
              <h4 className="text-lg font-bold text-gray-900">{plan.name}</h4>
              <div className="mt-2 mb-1">
                <span className="text-3xl font-bold text-gray-900">{plan.price}</span>
                <span className="text-sm text-gray-500">{plan.period}</span>
              </div>
              <p className="text-sm text-gray-500 mb-4">{plan.description}</p>
              <button
                className={`w-full py-2 px-4 text-sm font-medium rounded-lg transition-colors ${
                  plan.current
                    ? "bg-gray-100 text-gray-500 cursor-default"
                    : plan.name === "Enterprise"
                    ? "bg-gray-900 text-white hover:bg-gray-800"
                    : "bg-teal-600 text-white hover:bg-teal-700"
                }`}
                disabled={plan.current}
              >
                {plan.cta}
              </button>
              <ul className="mt-5 space-y-2.5">
                {plan.features.map((feat) => (
                  <li key={feat} className="flex items-center gap-2 text-sm text-gray-600">
                    <Check className="w-4 h-4 text-teal-500 flex-shrink-0" />
                    {feat}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Invoice history */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h3 className="text-base font-semibold text-gray-900">Invoice History</h3>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Invoice</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Date</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Amount</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Status</th>
              <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {invoiceHistory.map((inv) => (
              <tr key={inv.id} className="hover:bg-gray-50/50 transition-colors">
                <td className="px-5 py-3.5">
                  <span className="text-sm font-medium text-gray-900">{inv.id}</span>
                </td>
                <td className="px-5 py-3.5">
                  <span className="text-sm text-gray-500">{inv.date}</span>
                </td>
                <td className="px-5 py-3.5">
                  <span className="text-sm text-gray-900">{inv.amount}</span>
                </td>
                <td className="px-5 py-3.5">
                  <span className="inline-flex px-2.5 py-0.5 text-xs font-medium rounded-full bg-emerald-50 text-emerald-700">
                    {inv.status}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <button className="text-sm text-teal-600 hover:text-teal-800 font-medium transition-colors inline-flex items-center gap-1">
                    Download
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
