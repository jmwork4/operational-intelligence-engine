"use client";

import { useState } from "react";
import { UserPlus, MoreHorizontal } from "lucide-react";

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: "Admin" | "Operator" | "Viewer";
  status: "Active" | "Invited" | "Inactive";
  lastActive: string;
}

const mockMembers: TeamMember[] = [
  { id: "1", name: "Jocelyn Moore", email: "jocelyn@acmelogistics.com", role: "Admin", status: "Active", lastActive: "Just now" },
  { id: "2", name: "Marcus Chen", email: "marcus@acmelogistics.com", role: "Admin", status: "Active", lastActive: "2 hours ago" },
  { id: "3", name: "Priya Sharma", email: "priya@acmelogistics.com", role: "Operator", status: "Active", lastActive: "1 hour ago" },
  { id: "4", name: "James Rodriguez", email: "james@acmelogistics.com", role: "Operator", status: "Active", lastActive: "4 hours ago" },
  { id: "5", name: "Sarah Kim", email: "sarah@acmelogistics.com", role: "Operator", status: "Active", lastActive: "Yesterday" },
  { id: "6", name: "Alex Thompson", email: "alex@acmelogistics.com", role: "Viewer", status: "Active", lastActive: "3 days ago" },
  { id: "7", name: "Lisa Park", email: "lisa@acmelogistics.com", role: "Viewer", status: "Invited", lastActive: "Never" },
  { id: "8", name: "David Nguyen", email: "david@acmelogistics.com", role: "Viewer", status: "Inactive", lastActive: "2 weeks ago" },
];

const roleBadgeColors: Record<string, string> = {
  Admin: "bg-teal-50 text-teal-700",
  Operator: "bg-blue-50 text-blue-700",
  Viewer: "bg-gray-100 text-gray-600",
};

const statusDotColors: Record<string, string> = {
  Active: "bg-emerald-500",
  Invited: "bg-amber-400",
  Inactive: "bg-gray-300",
};

export default function TeamManagement() {
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("Viewer");

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Team Management</h2>
          <p className="text-sm text-gray-500 mt-1">
            Manage team members and their roles
          </p>
        </div>
        <button
          onClick={() => setShowInvite(!showInvite)}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          Invite Member
        </button>
      </div>

      {/* Invite form */}
      {showInvite && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Invite New Member</h3>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Email address</label>
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@company.com"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              />
            </div>
            <div className="w-40">
              <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent bg-white"
              >
                <option value="Admin">Admin</option>
                <option value="Operator">Operator</option>
                <option value="Viewer">Viewer</option>
              </select>
            </div>
            <button className="px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition-colors">
              Send Invite
            </button>
            <button
              onClick={() => setShowInvite(false)}
              className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Team table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Name</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Email</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Role</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Status</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">Last Active</th>
              <th className="text-right text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {mockMembers.map((member) => (
              <tr key={member.id} className="hover:bg-gray-50/50 transition-colors">
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                      <span className="text-xs font-medium text-gray-600">
                        {member.name.split(" ").map((n) => n[0]).join("")}
                      </span>
                    </div>
                    <span className="text-sm font-medium text-gray-900">{member.name}</span>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <span className="text-sm text-gray-500">{member.email}</span>
                </td>
                <td className="px-5 py-3.5">
                  <span className={`inline-flex px-2.5 py-0.5 text-xs font-medium rounded-full ${roleBadgeColors[member.role]}`}>
                    {member.role}
                  </span>
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${statusDotColors[member.status]}`} />
                    <span className="text-sm text-gray-600">{member.status}</span>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <span className="text-sm text-gray-500">{member.lastActive}</span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <button className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
                    <MoreHorizontal className="w-4 h-4" />
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
