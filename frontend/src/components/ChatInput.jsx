import { useState } from "react";
import { Send, Loader2 } from "lucide-react";

const EXAMPLE_PROMPTS = [
  "规划意大利 7 天蜜月旅行，重点体验美食和历史文化",
  "一个人去巴黎玩 5 天，喜欢艺术，预算适中",
  "带两个孩子去巴塞罗那，想体验文化和海滩",
];

export default function ChatInput({ onSend, disabled }) {
  const [message, setMessage] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleExample = (prompt) => {
    if (!disabled) {
      setMessage(prompt);
    }
  };

  return (
    <div className="bg-white border-t border-slate-200 p-4">
      {/* Example prompts */}
      {!disabled && !message && (
        <div className="mb-3 flex flex-wrap gap-2">
          {EXAMPLE_PROMPTS.map((prompt, i) => (
            <button
              key={i}
              onClick={() => handleExample(prompt)}
              className="text-xs bg-slate-50 hover:bg-blue-50 text-slate-600 hover:text-blue-700 px-3 py-1.5 rounded-full border border-slate-200 hover:border-blue-200 transition-colors"
            >
              {prompt.length > 50 ? prompt.slice(0, 50) + "..." : prompt}
            </button>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex gap-2">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder="描述你想要的旅行，例如：去杭州玩 3 天，喜欢美食和古迹"
          disabled={disabled}
          rows={2}
          className="flex-1 resize-none rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          aria-label="发送旅行想法"
          disabled={disabled || !message.trim()}
          className="self-end bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white p-3 rounded-xl transition-colors disabled:cursor-not-allowed"
        >
          {disabled ? (
            <Loader2 size={20} className="animate-spin" />
          ) : (
            <Send size={20} />
          )}
        </button>
      </form>
    </div>
  );
}
