import ReactMarkdown from "react-markdown";
import { Download, Copy, Check } from "lucide-react";
import { useState } from "react";
import { localizeRequest } from "../utils/localizeRequest";

export default function ItineraryDisplay({ itinerary, request, streaming = false }) {
  const [copied, setCopied] = useState(false);

  if (!itinerary) return null;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(itinerary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const content = `# 旅行行程\n\n## 原始需求\n\n${localizeRequest(request)}\n\n## 完整行程\n\n${itinerary}`;
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "旅行行程.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-4 my-3">
      {/* Header with actions */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-slate-700">
          {streaming ? "正在生成旅行行程…" : "你的旅行行程"}
        </h3>
        {!streaming && <div className="flex gap-1">
          <button
            onClick={handleCopy}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors text-slate-500 hover:text-slate-700"
            title="复制行程"
            aria-label="复制行程"
          >
            {copied ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
          </button>
          <button
            onClick={handleDownload}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors text-slate-500 hover:text-slate-700"
            title="下载行程"
            aria-label="下载行程"
          >
            <Download size={16} />
          </button>
        </div>}
      </div>

      {/* Original request */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
        <p className="text-xs font-medium text-blue-700 mb-1">你的需求</p>
        <p className="text-sm text-blue-900 whitespace-pre-wrap">{localizeRequest(request)}</p>
      </div>

      {/* Itinerary content */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 itinerary-content">
        <ReactMarkdown>{itinerary}</ReactMarkdown>
      </div>
    </div>
  );
}
