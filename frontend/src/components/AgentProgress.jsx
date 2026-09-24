import {
  Download,
  BookOpen,
  FileText,
  ClipboardList,
  CheckCircle2,
  Loader2,
  Circle,
} from "lucide-react";

const AGENT_ICONS = {
  planning: ClipboardList,
  data_fetch: Download,
  knowledge: BookOpen,
  compilation: FileText,
};

const AGENT_TEXT = {
  planning: { label: "分析旅行需求", description: "正在整理目的地、日期和偏好……" },
  data_fetch: { label: "查询实时信息", description: "正在查询航班、酒店、景点和天气……" },
  knowledge: { label: "整理旅行建议", description: "正在整理目的地的实用信息……" },
  compilation: { label: "生成旅行行程", description: "正在编排行程与预算……" },
};

function StatusIcon({ status }) {
  if (status === "completed") {
    return <CheckCircle2 size={18} className="text-green-500" />;
  }
  if (status === "running") {
    return <Loader2 size={18} className="text-blue-500 animate-spin" />;
  }
  return <Circle size={18} className="text-slate-300" />;
}

export default function AgentProgress({ agents, agentProgress }) {
  if (!agents.length) return null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 mx-4 my-3">
      <h3 className="text-sm font-semibold text-slate-700 mb-3">
        规划进度
      </h3>
      <div className="space-y-2">
        {agents.map((agent, i) => {
          const status = agentProgress[agent.key] || "pending";
          const Icon = AGENT_ICONS[agent.key] || Circle;
          const isActive = status === "running";

          return (
            <div key={agent.key}>
              <div
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all ${
                  isActive
                    ? "bg-blue-50 border border-blue-200"
                    : status === "completed"
                    ? "bg-green-50/50"
                    : "bg-slate-50"
                }`}
              >
                <Icon
                  size={16}
                  className={
                    isActive
                      ? "text-blue-600 animate-pulse-dot"
                      : status === "completed"
                      ? "text-green-600"
                      : "text-slate-400"
                  }
                />
                <div className="flex-1 min-w-0">
                  <p
                    className={`text-sm font-medium truncate ${
                      isActive
                        ? "text-blue-900"
                        : status === "completed"
                        ? "text-green-800"
                        : "text-slate-500"
                    }`}
                  >
                    {AGENT_TEXT[agent.key]?.label || "正在处理"}
                  </p>
                  {isActive && (
                    <p className="text-xs text-blue-600 mt-0.5">
                      {AGENT_TEXT[agent.key]?.description || "正在处理……"}
                    </p>
                  )}
                </div>
                <StatusIcon status={status} />
              </div>
              {/* Connector line */}
              {i < agents.length - 1 && (
                <div className="flex justify-center">
                  <div
                    className={`w-px h-2 ${
                      status === "completed" ? "bg-green-300" : "bg-slate-200"
                    }`}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
