import { FileText, Upload, Search } from "lucide-react";

const documents = [
  { id: "DOC-041", title: "Fleet Safety Procedures v3.2", type: "PDF", size: "2.4 MB", chunks: 48, status: "indexed", uploaded: "Mar 14, 2026" },
  { id: "DOC-040", title: "Vendor SLA Agreements — Q1 2026", type: "PDF", size: "1.8 MB", chunks: 32, status: "indexed", uploaded: "Mar 12, 2026" },
  { id: "DOC-039", title: "Warehouse Operations Manual", type: "PDF", size: "5.1 MB", chunks: 96, status: "indexed", uploaded: "Mar 10, 2026" },
  { id: "DOC-038", title: "Driver Onboarding Checklist", type: "DOCX", size: "340 KB", chunks: 12, status: "indexed", uploaded: "Mar 8, 2026" },
  { id: "DOC-037", title: "Cold Chain Compliance Standards", type: "PDF", size: "3.2 MB", chunks: 64, status: "indexed", uploaded: "Mar 5, 2026" },
  { id: "DOC-036", title: "Route Optimization Guidelines", type: "PDF", size: "1.1 MB", chunks: 24, status: "indexed", uploaded: "Mar 3, 2026" },
  { id: "DOC-035", title: "Incident Response Playbook", type: "PDF", size: "890 KB", chunks: 18, status: "indexed", uploaded: "Feb 28, 2026" },
  { id: "DOC-034", title: "Q4 2025 Operations Review", type: "PDF", size: "4.6 MB", chunks: 82, status: "indexed", uploaded: "Feb 20, 2026" },
];

export default function DocumentsPage() {
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Documents</h2>
          <p className="text-sm text-gray-500 mt-1">
            {documents.length} documents &middot; 376 chunks indexed
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors">
          <Upload className="w-4 h-4" />
          Upload Document
        </button>
      </div>

      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Semantic search across all documents..."
          className="w-full pl-11 pr-4 py-3 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
        />
      </div>

      {/* Document grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {documents.map((doc) => (
          <div key={doc.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow cursor-pointer">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-teal-50 flex items-center justify-center flex-shrink-0">
                <FileText className="w-5 h-5 text-teal-600" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-gray-900 truncate">{doc.title}</h3>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-xs text-gray-400 font-mono">{doc.id}</span>
                  <span className="text-gray-300">&middot;</span>
                  <span className="text-xs text-gray-500">{doc.type}</span>
                  <span className="text-gray-300">&middot;</span>
                  <span className="text-xs text-gray-500">{doc.size}</span>
                </div>
                <div className="flex items-center justify-between mt-3">
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700">
                      {doc.chunks} chunks
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-teal-50 text-teal-700">
                      {doc.status}
                    </span>
                  </div>
                  <span className="text-xs text-gray-400">{doc.uploaded}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
