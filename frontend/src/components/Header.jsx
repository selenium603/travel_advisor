import { Globe, Menu } from "lucide-react";

export default function Header({ onToggleSidebar }) {
  return (
    <header className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          aria-label="查看历史行程"
          className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <Menu size={20} className="text-slate-600" />
        </button>
        <div className="flex items-center gap-2">
          <div className="bg-blue-600 p-2 rounded-lg">
            <Globe size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 leading-tight">
              智能旅行规划
            </h1>
            <p className="text-xs text-slate-500">
              为你规划每一段旅程
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}
