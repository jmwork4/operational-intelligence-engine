import { Sparkles, Send } from "lucide-react";

const conversation = [
  {
    role: "user",
    message: "Why are shipments from Vendor X consistently delayed this week?",
    time: "10:32 AM",
  },
  {
    role: "assistant",
    message: `Based on analysis of 47 events from Vendor X over the past 7 days, I identified three primary delay factors:

**1. Port Congestion (62% of delays)**
Vendor X ships through the Port of Savannah, which has experienced 3-day average processing delays since March 10th due to increased container volume.

**2. Route Capacity Issues (24% of delays)**
The I-95 corridor used for 80% of Vendor X shipments has active construction zones causing 30-45 minute delays during peak hours.

**3. Carrier Availability (14% of delays)**
Vendor X's primary carrier (TransCo) has reduced fleet capacity by 15% this month for scheduled maintenance.

**Recommendation:** Consider routing Vendor X shipments through the alternate I-85 corridor and requesting TransCo provide backup carrier assignments for the next 2 weeks.

*Sources: Fleet Safety Procedures v3.2, Vendor SLA Agreements — Q1 2026*`,
    time: "10:32 AM",
    telemetry: { model: "Claude Sonnet", tokens: "1,247", latency: "3.1s", sources: 2 },
  },
  {
    role: "user",
    message: "What's the financial impact of these delays?",
    time: "10:34 AM",
  },
  {
    role: "assistant",
    message: `Analyzing delay costs against SLA agreements and operational data:

**Direct Costs (past 7 days):**
- SLA penalty charges: **$12,400** (4 breaches × $3,100 avg penalty)
- Expedited reshipping: **$8,200** (3 emergency reroutes)
- Warehouse overtime labor: **$3,800** (delayed receiving windows)

**Estimated Indirect Costs:**
- Customer satisfaction impact: 3 affected accounts flagged risk of churn
- Inventory carrying cost increase: ~$2,100/day for safety stock buffer

**Total 7-day impact: ~$26,500**

If current patterns continue, projected monthly impact would be approximately **$106,000**. The I-85 rerouting recommendation from my previous analysis could reduce this by an estimated 40-55%.`,
    time: "10:34 AM",
    telemetry: { model: "Claude Sonnet", tokens: "892", latency: "2.8s", sources: 3 },
  },
];

export default function AICopilotPage() {
  return (
    <div className="max-w-4xl mx-auto flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900">AI Copilot</h2>
        <p className="text-sm text-gray-500 mt-1">
          Ask questions about your operations — powered by your events, rules, and documents
        </p>
      </div>

      {/* Conversation */}
      <div className="flex-1 overflow-y-auto space-y-6 pb-4">
        {conversation.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] ${msg.role === "user" ? "order-1" : ""}`}>
              <div
                className={`rounded-2xl px-5 py-4 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-teal-600 text-white"
                    : "bg-white shadow-sm border border-gray-100 text-gray-700"
                }`}
              >
                {msg.role === "assistant" ? (
                  <div className="prose prose-sm max-w-none">
                    {msg.message.split("\n").map((line, j) => {
                      if (line.startsWith("**") && line.endsWith("**")) {
                        return <p key={j} className="font-semibold text-gray-900 mt-3 first:mt-0">{line.replace(/\*\*/g, "")}</p>;
                      }
                      if (line.startsWith("- ")) {
                        return <p key={j} className="ml-3 text-gray-600">{line}</p>;
                      }
                      if (line.startsWith("*") && line.endsWith("*")) {
                        return <p key={j} className="text-xs text-gray-400 mt-3 italic">{line.replace(/\*/g, "")}</p>;
                      }
                      if (line === "") return <div key={j} className="h-2" />;
                      return <p key={j}>{line.replace(/\*\*/g, "")}</p>;
                    })}
                  </div>
                ) : (
                  msg.message
                )}
              </div>
              <div className={`flex items-center gap-3 mt-1.5 px-2 ${msg.role === "user" ? "justify-end" : ""}`}>
                <span className="text-xs text-gray-400">{msg.time}</span>
                {"telemetry" in msg && msg.telemetry && (
                  <>
                    <span className="text-gray-300">&middot;</span>
                    <span className="text-xs text-gray-400">{msg.telemetry.model}</span>
                    <span className="text-gray-300">&middot;</span>
                    <span className="text-xs text-gray-400">{msg.telemetry.tokens} tokens</span>
                    <span className="text-gray-300">&middot;</span>
                    <span className="text-xs text-gray-400">{msg.telemetry.latency}</span>
                    <span className="text-gray-300">&middot;</span>
                    <span className="text-xs text-gray-400">{msg.telemetry.sources} sources</span>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 pt-4">
        <div className="flex items-center gap-3">
          <div className="flex-1 relative">
            <Sparkles className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-teal-500" />
            <input
              type="text"
              placeholder="Ask about your operations..."
              className="w-full pl-11 pr-4 py-3 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
            />
          </div>
          <button className="p-3 bg-teal-600 text-white rounded-xl hover:bg-teal-700 transition-colors">
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          AI responses are generated using your operational data and documents. All queries are logged and observable.
        </p>
      </div>
    </div>
  );
}
