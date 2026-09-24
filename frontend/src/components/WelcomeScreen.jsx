import { Globe, Plane, Hotel, MapPin, Sparkles } from "lucide-react";
import { createElement } from "react";

const FEATURES = [
  { icon: Plane, title: "航班查询", desc: "查找合适的航班" },
  { icon: Hotel, title: "酒店推荐", desc: "筛选合适的住宿" },
  { icon: MapPin, title: "景点活动", desc: "发现景点与体验" },
  { icon: Sparkles, title: "智能规划", desc: "综合信息生成行程" },
];

export default function WelcomeScreen() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
      <div className="bg-blue-100 p-4 rounded-2xl mb-4">
        <Globe size={40} className="text-blue-600" />
      </div>
      <h2 className="text-2xl font-bold text-slate-900 mb-2">
        规划你的理想旅程
      </h2>
      <p className="text-slate-500 max-w-md mb-8">
        说说你想去哪里、喜欢什么。我们会查询航班、酒店和景点，
        为你生成逐日行程。
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-lg">
        {FEATURES.map(({ icon, title, desc }) => (
          <div
            key={title}
            className="bg-white border border-slate-200 rounded-xl p-4 text-center"
          >
            {createElement(icon, { size: 24, className: "text-blue-600 mx-auto mb-2" })}
            <p className="text-sm font-medium text-slate-800">{title}</p>
            <p className="text-xs text-slate-500 mt-1">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
