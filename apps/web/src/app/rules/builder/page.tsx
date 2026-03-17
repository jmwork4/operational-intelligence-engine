"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Plus, Trash2, Eye } from "lucide-react";

type RuleType = "event_triggered" | "threshold" | "composite" | null;
type Operator = ">" | "<" | "==" | "!=" | ">=" | "<=";
type LogicOp = "AND" | "OR";
type Severity = "low" | "medium" | "high" | "critical";
type ActionType = "alert" | "notification" | "webhook";

interface Condition {
  id: string;
  field: string;
  operator: Operator;
  value: string;
  logic: LogicOp;
}

const fields = [
  "event.delay_minutes",
  "event.vendor_priority",
  "event.temperature",
  "event.deviation_km",
  "event.stock_level",
  "event.mileage",
  "event.actual_time",
  "event.promised_time",
  "event.idle_hours",
  "event.speed_mph",
];

const operators: { value: Operator; label: string }[] = [
  { value: ">", label: ">" },
  { value: "<", label: "<" },
  { value: "==", label: "==" },
  { value: "!=", label: "!=" },
  { value: ">=", label: ">=" },
  { value: "<=", label: "<=" },
];

const ruleTypeCards: { type: RuleType; title: string; desc: string; color: string }[] = [
  {
    type: "event_triggered",
    title: "Event-Triggered",
    desc: "Fires when a single event matches conditions",
    color: "border-blue-400 bg-blue-50 text-blue-700",
  },
  {
    type: "threshold",
    title: "Threshold",
    desc: "Fires when a metric exceeds a threshold over a time window",
    color: "border-purple-400 bg-purple-50 text-purple-700",
  },
  {
    type: "composite",
    title: "Composite",
    desc: "Combines multiple event types with temporal logic",
    color: "border-amber-400 bg-amber-50 text-amber-700",
  },
];

export default function RuleBuilderPage() {
  const [step, setStep] = useState(1);
  const [ruleType, setRuleType] = useState<RuleType>(null);
  const [conditions, setConditions] = useState<Condition[]>([
    { id: "c1", field: fields[0], operator: ">", value: "", logic: "AND" },
  ]);
  const [severity, setSeverity] = useState<Severity>("medium");
  const [actionType, setActionType] = useState<ActionType>("alert");
  const [ruleName, setRuleName] = useState("");
  const [evalWindow, setEvalWindow] = useState("5m");

  const addCondition = (logic: LogicOp) => {
    setConditions((prev) => [
      ...prev,
      {
        id: `c${Date.now()}`,
        field: fields[0],
        operator: ">",
        value: "",
        logic,
      },
    ]);
  };

  const removeCondition = (id: string) => {
    if (conditions.length > 1) {
      setConditions((prev) => prev.filter((c) => c.id !== id));
    }
  };

  const updateCondition = (id: string, key: keyof Condition, value: string) => {
    setConditions((prev) =>
      prev.map((c) => (c.id === id ? { ...c, [key]: value } : c))
    );
  };

  const buildExpression = () => {
    const parts = conditions.map((c, i) => {
      const expr = `${c.field} ${c.operator} ${c.value || "?"}`;
      if (i === 0) return expr;
      return `${c.logic} ${expr}`;
    });
    let expression = parts.join(" ");
    if (ruleType === "threshold" && evalWindow) {
      expression += ` FOR ${evalWindow}`;
    }
    return expression;
  };

  const handleCreate = () => {
    const config = {
      name: ruleName,
      type: ruleType,
      conditions,
      severity,
      actionType,
      evalWindow: ruleType !== "event_triggered" ? evalWindow : undefined,
      expression: buildExpression(),
    };
    console.log("Rule created:", config);
    alert("Rule created! Check console for config.");
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/rules"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Rule Builder</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Create rules visually without writing code
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main builder */}
        <div className="lg:col-span-2 space-y-6">
          {/* Step 1: Rule Type */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="w-7 h-7 rounded-full bg-teal-600 text-white text-xs font-bold flex items-center justify-center">
                1
              </span>
              <h3 className="text-sm font-semibold text-gray-900">
                Choose Rule Type
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {ruleTypeCards.map((card) => (
                <button
                  key={card.type}
                  onClick={() => {
                    setRuleType(card.type);
                    setStep(Math.max(step, 2));
                  }}
                  className={`p-4 rounded-lg border-2 text-left transition-all ${
                    ruleType === card.type
                      ? card.color + " ring-2 ring-offset-1 ring-teal-400"
                      : "border-gray-200 hover:border-gray-300 bg-white"
                  }`}
                >
                  <p className="text-sm font-semibold">{card.title}</p>
                  <p className="text-xs text-gray-500 mt-1">{card.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Step 2: Conditions */}
          {step >= 2 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center gap-2 mb-4">
                <span className="w-7 h-7 rounded-full bg-teal-600 text-white text-xs font-bold flex items-center justify-center">
                  2
                </span>
                <h3 className="text-sm font-semibold text-gray-900">
                  Configure Conditions
                </h3>
              </div>
              <div className="space-y-3">
                {conditions.map((cond, i) => (
                  <div key={cond.id} className="flex items-center gap-2">
                    {i > 0 && (
                      <span className="text-xs font-bold text-gray-400 w-10 text-center">
                        {cond.logic}
                      </span>
                    )}
                    {i === 0 && <span className="w-10" />}
                    <select
                      value={cond.field}
                      onChange={(e) =>
                        updateCondition(cond.id, "field", e.target.value)
                      }
                      className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-teal-400"
                    >
                      {fields.map((f) => (
                        <option key={f} value={f}>
                          {f}
                        </option>
                      ))}
                    </select>
                    <select
                      value={cond.operator}
                      onChange={(e) =>
                        updateCondition(cond.id, "operator", e.target.value)
                      }
                      className="w-20 px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-teal-400"
                    >
                      {operators.map((op) => (
                        <option key={op.value} value={op.value}>
                          {op.label}
                        </option>
                      ))}
                    </select>
                    <input
                      type="text"
                      placeholder="Value"
                      value={cond.value}
                      onChange={(e) =>
                        updateCondition(cond.id, "value", e.target.value)
                      }
                      className="w-28 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                    />
                    <button
                      onClick={() => removeCondition(cond.id)}
                      className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                      disabled={conditions.length === 1}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2 mt-4">
                <button
                  onClick={() => {
                    addCondition("AND");
                    setStep(Math.max(step, 3));
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-teal-700 bg-teal-50 rounded-lg hover:bg-teal-100 transition-colors"
                >
                  <Plus className="w-3 h-3" /> AND
                </button>
                <button
                  onClick={() => {
                    addCondition("OR");
                    setStep(Math.max(step, 3));
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <Plus className="w-3 h-3" /> OR
                </button>
                <button
                  onClick={() => setStep(Math.max(step, 3))}
                  className="ml-auto px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Severity & Action */}
          {step >= 3 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center gap-2 mb-4">
                <span className="w-7 h-7 rounded-full bg-teal-600 text-white text-xs font-bold flex items-center justify-center">
                  3
                </span>
                <h3 className="text-sm font-semibold text-gray-900">
                  Set Severity & Action
                </h3>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Severity
                  </label>
                  <select
                    value={severity}
                    onChange={(e) => setSeverity(e.target.value as Severity)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-teal-400"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Action Type
                  </label>
                  <select
                    value={actionType}
                    onChange={(e) => setActionType(e.target.value as ActionType)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-teal-400"
                  >
                    <option value="alert">Alert</option>
                    <option value="notification">Notification</option>
                    <option value="webhook">Webhook</option>
                  </select>
                </div>
              </div>
              <button
                onClick={() => setStep(Math.max(step, 4))}
                className="mt-4 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Next
              </button>
            </div>
          )}

          {/* Step 4: Name & Window */}
          {step >= 4 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center gap-2 mb-4">
                <span className="w-7 h-7 rounded-full bg-teal-600 text-white text-xs font-bold flex items-center justify-center">
                  4
                </span>
                <h3 className="text-sm font-semibold text-gray-900">
                  Name & Finalize
                </h3>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Rule Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., Late Shipment Alert"
                    value={ruleName}
                    onChange={(e) => setRuleName(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                  />
                </div>
                {ruleType !== "event_triggered" && (
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Evaluation Window
                    </label>
                    <select
                      value={evalWindow}
                      onChange={(e) => setEvalWindow(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-teal-400"
                    >
                      <option value="1m">1 minute</option>
                      <option value="5m">5 minutes</option>
                      <option value="10m">10 minutes</option>
                      <option value="30m">30 minutes</option>
                      <option value="1h">1 hour</option>
                      <option value="2h">2 hours</option>
                      <option value="6h">6 hours</option>
                      <option value="24h">24 hours</option>
                      <option value="7d">7 days</option>
                    </select>
                  </div>
                )}
                <button
                  onClick={handleCreate}
                  disabled={!ruleName || !ruleType}
                  className="w-full px-4 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Create Rule
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Preview Panel */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 sticky top-8">
            <div className="flex items-center gap-2 mb-4">
              <Eye className="w-4 h-4 text-teal-600" />
              <h3 className="text-sm font-semibold text-gray-900">
                Live Preview
              </h3>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-400 mb-1">Name</p>
                <p className="text-sm font-medium text-gray-900">
                  {ruleName || "Untitled Rule"}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">Type</p>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                    ruleType === "event_triggered"
                      ? "bg-blue-50 text-blue-700"
                      : ruleType === "threshold"
                      ? "bg-purple-50 text-purple-700"
                      : ruleType === "composite"
                      ? "bg-amber-50 text-amber-700"
                      : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {ruleType
                    ? ruleType.replace("_", " ")
                    : "Not selected"}
                </span>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">Severity</p>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                    severity === "critical"
                      ? "bg-red-50 text-red-700"
                      : severity === "high"
                      ? "bg-orange-50 text-orange-700"
                      : severity === "medium"
                      ? "bg-yellow-50 text-yellow-700"
                      : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {severity}
                </span>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">Action</p>
                <p className="text-sm text-gray-700 capitalize">{actionType}</p>
              </div>
              {ruleType !== "event_triggered" && ruleType && (
                <div>
                  <p className="text-xs text-gray-400 mb-1">Window</p>
                  <p className="text-sm text-gray-700">{evalWindow}</p>
                </div>
              )}
              <div>
                <p className="text-xs text-gray-400 mb-1">Expression</p>
                <code className="block text-xs bg-gray-50 text-gray-700 px-3 py-2 rounded-lg font-mono break-all">
                  {buildExpression()}
                </code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
