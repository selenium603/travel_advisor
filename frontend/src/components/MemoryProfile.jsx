import { useEffect, useState } from "react";
import { ArrowLeft, Save, Trash2 } from "lucide-react";

const CATEGORIES = [
  ["lodging", "住宿偏好"],
  ["food", "饮食偏好"],
  ["pace", "行程节奏"],
  ["sights", "景点偏好"],
  ["budget", "长期预算"],
];

export default function MemoryProfile({ sessionId, onBack, onProfileChange }) {
  const [profile, setProfile] = useState({ preferences: {}, changes: [] });
  const [session, setSession] = useState({});
  const [drafts, setDrafts] = useState({});
  const [message, setMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const [profileResponse, sessionResponse] = await Promise.all([
      fetch("/api/memory/profile"),
      fetch(`/api/memory/sessions/${encodeURIComponent(sessionId)}`),
    ]);
    if (!profileResponse.ok || !sessionResponse.ok) throw new Error("无法读取记忆");
    const [nextProfile, nextSession] = await Promise.all([
      profileResponse.json(), sessionResponse.json(),
    ]);
    setProfile(nextProfile);
    setSession(nextSession);
    setDrafts(Object.fromEntries(CATEGORIES.map(([key]) => [key, nextProfile.preferences[key]?.value || ""])));
    onProfileChange(nextProfile.preferences);
  };

  useEffect(() => {
    // Refresh only when this panel is opened or the session changes.
    let active = true;
    Promise.all([
      fetch("/api/memory/profile").then((response) => response.json()),
      fetch(`/api/memory/sessions/${encodeURIComponent(sessionId)}`).then((response) => response.json()),
    ]).then(([nextProfile, nextSession]) => {
      if (!active) return;
      setProfile(nextProfile);
      setSession(nextSession);
      setDrafts(Object.fromEntries(CATEGORIES.map(([key]) => [key, nextProfile.preferences[key]?.value || ""])));
    }).catch(() => { if (active) setNotice("无法读取记忆，请刷新重试。"); });
    return () => { active = false; };
  }, [sessionId]);

  const run = async (action, success) => {
    setBusy(true);
    setNotice("");
    try {
      await action();
      await refresh();
      setNotice(success);
    } catch (error) {
      setNotice(error.message || "操作失败，请重试。");
    } finally {
      setBusy(false);
    }
  };

  const save = (category) => run(async () => {
    const response = await fetch(`/api/memory/preferences/${category}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value: drafts[category]?.trim() }),
    });
    if (!response.ok) throw new Error("保存失败，请检查内容。");
  }, "偏好已保存；同类别的旧偏好已更新。");

  const remove = (category) => run(async () => {
    const response = await fetch(`/api/memory/preferences/${category}`, { method: "DELETE" });
    if (!response.ok) throw new Error("删除失败。");
  }, "偏好已删除。");

  const rememberText = () => run(async () => {
    const response = await fetch("/api/memory/preferences/extract", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message.trim(), session_id: sessionId }),
    });
    if (!response.ok) throw new Error("暂时无法识别这句话，请使用下方分类手动填写。");
    const result = await response.json();
    if (!result.updates.length) throw new Error("没有识别到明确的长期偏好，请写明‘以后我更喜欢……’。");
    setMessage("");
  }, "已记住新的长期偏好。");

  return (
    <div className="max-w-3xl mx-auto p-4 sm:p-6 space-y-6">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-600 hover:text-blue-700">
        <ArrowLeft size={16} /> 返回行程
      </button>
      <div>
        <h2 className="text-xl font-bold text-slate-900">我的旅行记忆</h2>
        <p className="text-sm text-slate-500 mt-1">长期偏好会用于后续规划和住宿查询；当前行程的表单内容始终优先。</p>
      </div>

      <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
        <h3 className="font-semibold text-slate-800">用一句话更新偏好</h3>
        <div className="flex gap-2">
          <input value={message} onChange={(event) => setMessage(event.target.value)}
            placeholder="例如：以后住宿我更喜欢四五星酒店"
            className="flex-1 min-w-0 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <button disabled={busy || !message.trim()} onClick={rememberText}
            className="rounded-lg bg-blue-600 disabled:bg-slate-300 text-white px-4 py-2 text-sm">记住</button>
        </div>
        <p className="text-xs text-slate-500">这句话会交给当前配置的模型识别；你也可以直接编辑下方偏好。</p>
      </section>

      {notice && <p role="status" className="text-sm text-blue-700">{notice}</p>}

      <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-4">
        <h3 className="font-semibold text-slate-800">长期偏好</h3>
        {CATEGORIES.map(([category, label]) => {
          const entry = profile.preferences[category];
          return <div key={category} className="border-t border-slate-100 pt-3">
            <label htmlFor={`memory-${category}`} className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
            <div className="flex gap-2">
              <input id={`memory-${category}`} value={drafts[category] || ""}
                onChange={(event) => setDrafts((old) => ({ ...old, [category]: event.target.value }))}
                className="flex-1 min-w-0 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="尚未设置" />
              <button aria-label={`保存${label}`} disabled={busy || !drafts[category]?.trim()}
                onClick={() => save(category)} className="p-2 rounded-lg text-blue-600 disabled:text-slate-300 hover:bg-blue-50"><Save size={18} /></button>
              <button aria-label={`删除${label}`} disabled={busy || !entry}
                onClick={() => remove(category)} className="p-2 rounded-lg text-red-500 disabled:text-slate-300 hover:bg-red-50"><Trash2 size={18} /></button>
            </div>
            {entry && <p className="text-xs text-slate-500 mt-1">
              更新于 {new Date(entry.updated_at).toLocaleString("zh-CN")} · 来源：{entry.source.kind === "manual_edit" ? "手动修改" : entry.source.quote}
            </p>}
          </div>;
        })}
      </section>

      {profile.changes?.length > 0 && <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-2">
        <h3 className="font-semibold text-slate-800">最近更新</h3>
        {profile.changes.slice(-5).reverse().map((change, index) => <p key={`${change.updated_at}-${index}`}
          className="text-xs text-slate-600 border-t border-slate-100 pt-2">
          {CATEGORIES.find(([key]) => key === change.category)?.[1] || change.category}：
          {change.old_value ? `${change.old_value} → ` : ""}{change.new_value}
          <span className="text-slate-400"> · {new Date(change.updated_at).toLocaleString("zh-CN")}</span>
        </p>)}
      </section>}

      <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-2">
        <h3 className="font-semibold text-slate-800">当前会话</h3>
        <p className="text-sm text-slate-600">状态：{session.current_plan_state || "尚未开始"}</p>
        {session.current_plan?.destinations && <p className="text-sm text-slate-600">
          本轮目的地：{session.current_plan.destinations.join("、")} · {session.current_plan.travelers} 人
        </p>}
        <p className="text-xs text-slate-500">最近消息：{session.recent_messages?.length || 0} 条</p>
        {session.recent_messages?.slice(-4).map((item, index) => <p key={`${item.at}-${index}`}
          className="text-xs text-slate-500 truncate">
          {item.role === "user" ? "你" : "规划助手"}：{item.content}
        </p>)}
        {session.recent_messages?.length > 0 && <button disabled={busy}
          onClick={() => run(async () => {
            const response = await fetch(`/api/memory/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
            if (!response.ok) throw new Error("清除失败。");
          }, "本次会话记忆已清除。")}
          className="text-xs text-red-600 hover:text-red-700">清除本次会话记忆</button>}
      </section>
    </div>
  );
}
