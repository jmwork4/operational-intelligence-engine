"use client";

import Link from "next/link";
import { Users, Key, CreditCard, ArrowUpRight, Zap, Brain, HardDrive, UserCheck } from "lucide-react";

const usageStats = [
  { label: "Events This Month", value: "45,230", icon: Zap, color: "text-blue-600", bg: "bg-blue-50" },
  { label: "AI Queries", value: "1,847", icon: Brain, color: "text-purple-600", bg: "bg-purple-50" },
  { label: "Storage Used", value: "12.4 GB", icon: HardDrive, color: "text-teal-600", bg: "bg-teal-50" },
  { label: "Team Members", value: "8", icon: UserCheck, color: "text-amber-600", bg: "bg-amber-50" },
];

const adminLinks = [
  { label: "Team Management", description: "Invite members, manage roles and permissions", href: "/admin/team", icon: Users, color: "text-blue-600" },
  { label: "API Keys", description: "Generate and manage API keys for integrations", href: "/admin/api-keys", icon: Key, color: "text-teal-600" },
  { label: "Billing & Plans", description: "View invoices, manage subscription and usage", href: "/admin/billing", icon: CreditCard, color: "text-purple-600" },
];

export default function AdminDashboard() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Page heading */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Admin Dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">
          Manage your organization, team, and billing
        </p>
      </div>

      {/* Usage stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {usageStats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between">
                <div className={`w-10 h-10 rounded-lg ${stat.bg} flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${stat.color}`} />
                </div>
              </div>
              <div className="mt-3">
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                <p className="text-sm text-gray-500 mt-0.5">{stat.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Current plan + Billing summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Current Plan */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-gray-900">Current Plan</h3>
            <span className="px-2.5 py-1 text-xs font-medium bg-teal-50 text-teal-700 rounded-full">
              Professional
            </span>
          </div>
          <p className="text-sm text-gray-500 mb-4">
            You are on the <span className="font-medium text-gray-700">Professional</span> plan
            with access to advanced analytics, AI queries, and priority support.
          </p>
          <div className="flex items-center gap-3">
            <Link
              href="/admin/billing"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition-colors"
            >
              Upgrade Plan
              <ArrowUpRight className="w-4 h-4" />
            </Link>
            <Link
              href="/admin/billing"
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              View all plans
            </Link>
          </div>
        </div>

        {/* Billing Summary */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-base font-semibold text-gray-900 mb-4">Billing Summary</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Next invoice</span>
              <span className="text-sm font-semibold text-gray-900">$200.00</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Due date</span>
              <span className="text-sm text-gray-700">April 1, 2026</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Payment method</span>
              <span className="text-sm text-gray-700">Visa ending 4242</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Billing cycle</span>
              <span className="text-sm text-gray-700">Monthly</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {adminLinks.map((link) => {
          const Icon = link.icon;
          return (
            <Link
              key={link.label}
              href={link.href}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:border-gray-300 hover:shadow-sm transition-all group"
            >
              <div className="flex items-center gap-3 mb-2">
                <Icon className={`w-5 h-5 ${link.color}`} />
                <h3 className="text-sm font-semibold text-gray-900 group-hover:text-teal-700 transition-colors">
                  {link.label}
                </h3>
              </div>
              <p className="text-sm text-gray-500">{link.description}</p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
