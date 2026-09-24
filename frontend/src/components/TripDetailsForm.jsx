import { useState } from "react";
import { ArrowLeft, Send, Loader2, Calendar, Users, Wallet, Heart } from "lucide-react";
import LocalizedDateInput from "./LocalizedDateInput";

const BUDGET_OPTIONS = [
  { value: "budget", label: "经济型", desc: "青旅、小吃、公共交通" },
  { value: "mid-range", label: "舒适型", desc: "舒适酒店、当地餐厅" },
  { value: "luxury", label: "豪华型", desc: "高端酒店、精致餐饮" },
  { value: "ultra-luxury", label: "奢华型", desc: "顶级套房、私人行程" },
];

const INTEREST_OPTIONS = [
  { value: "Food & Cuisine", label: "美食" },
  { value: "History & Culture", label: "历史文化" },
  { value: "Art & Museums", label: "艺术与博物馆" },
  { value: "Adventure & Outdoors", label: "户外探险" },
  { value: "Beaches & Relaxation", label: "海滩休闲" },
  { value: "Nightlife", label: "夜生活" },
  { value: "Shopping", label: "购物" },
  { value: "Architecture", label: "建筑" },
  { value: "Nature & Wildlife", label: "自然与野生动物" },
  { value: "Photography", label: "摄影" },
  { value: "Wine & Spirits", label: "葡萄酒与烈酒" },
  { value: "Family Fun", label: "亲子活动" },
];

export default function TripDetailsForm({ tripIdea, onSubmit, onBack, disabled }) {
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;

  const [form, setForm] = useState({
    startDate: "",
    endDate: "",
    travelers: "2",
    travelerDetails: "",
    budget: "mid-range",
    interests: [],
    specialRequirements: "",
    departureCity: "",
  });

  const [errors, setErrors] = useState({});

  const update = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: null }));
  };

  const toggleInterest = (interest) => {
    setForm((prev) => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter((i) => i !== interest)
        : [...prev.interests, interest],
    }));
  };

  const validate = () => {
    const errs = {};
    if (!form.startDate) errs.startDate = "请选择出发日期";
    if (!form.endDate) errs.endDate = "请选择返程日期";
    if (form.startDate && form.endDate && form.startDate >= form.endDate) {
      errs.endDate = "返程日期必须晚于出发日期";
    }
    if (form.startDate && form.startDate < today) {
      errs.startDate = "出发日期不能早于今天";
    }
    if (!form.departureCity.trim()) errs.departureCity = "请输入出发城市";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate() || disabled) return;

    // Calculate trip duration
    const start = new Date(form.startDate);
    const end = new Date(form.endDate);
    const days = Math.ceil((end - start) / (1000 * 60 * 60 * 24));

    // Build structured prompt
    const prompt = [
      `Trip Request: ${tripIdea}`,
      ``,
      `Essential Details:`,
      `- Travel Dates: ${form.startDate} to ${form.endDate} (${days} days)`,
      `- Departure City: ${form.departureCity}`,
      `- Number of Travelers: ${form.travelers}`,
      form.travelerDetails ? `- Traveler Details: ${form.travelerDetails}` : null,
      `- Budget Level: ${form.budget}`,
      form.interests.length > 0 ? `- Interests: ${form.interests.join(", ")}` : null,
      form.specialRequirements ? `- Special Requirements: ${form.specialRequirements}` : null,
    ]
      .filter(Boolean)
      .join("\n");

    onSubmit(prompt);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={onBack}
            className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-3 transition-colors"
          >
            <ArrowLeft size={16} />
            修改旅行想法
          </button>
          <h2 className="text-xl font-bold text-slate-900">行程详情</h2>
          <div className="mt-2 bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-blue-800">{tripIdea}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Departure City */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              出发城市 *
            </label>
            <input
              type="text"
              value={form.departureCity}
              onChange={(e) => update("departureCity", e.target.value)}
              placeholder="例如：北京、上海、广州"
              className={`w-full rounded-lg border px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.departureCity ? "border-red-300" : "border-slate-300"
              }`}
            />
            {errors.departureCity && (
              <p className="text-xs text-red-500 mt-1">{errors.departureCity}</p>
            )}
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="startDate" className="block text-sm font-medium text-slate-700 mb-1.5">
                <Calendar size={14} className="inline mr-1" />
                出发日期 *
              </label>
              <LocalizedDateInput
                id="startDate"
                label="出发日期"
                value={form.startDate}
                min={today}
                onChange={(value) => update("startDate", value)}
                invalid={Boolean(errors.startDate)}
              />
              {errors.startDate && (
                <p className="text-xs text-red-500 mt-1">{errors.startDate}</p>
              )}
            </div>
            <div>
              <label htmlFor="endDate" className="block text-sm font-medium text-slate-700 mb-1.5">
                <Calendar size={14} className="inline mr-1" />
                返程日期 *
              </label>
              <LocalizedDateInput
                id="endDate"
                label="返程日期"
                value={form.endDate}
                min={form.startDate || today}
                onChange={(value) => update("endDate", value)}
                invalid={Boolean(errors.endDate)}
              />
              {errors.endDate && (
                <p className="text-xs text-red-500 mt-1">{errors.endDate}</p>
              )}
            </div>
          </div>

          {/* Travelers */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                <Users size={14} className="inline mr-1" />
                出行人数
              </label>
              <select
                value={form.travelers}
                onChange={(e) => update("travelers", e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
                  <option key={n} value={n}>
                    {n} 人
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                同行人说明
              </label>
              <input
                type="text"
                value={form.travelerDetails}
                onChange={(e) => update("travelerDetails", e.target.value)}
                placeholder="例如：情侣出行、带两名儿童的家庭"
                className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Budget */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              <Wallet size={14} className="inline mr-1" />
              预算档次
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {BUDGET_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => update("budget", opt.value)}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    form.budget === opt.value
                      ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <p
                    className={`text-sm font-medium ${
                      form.budget === opt.value ? "text-blue-700" : "text-slate-700"
                    }`}
                  >
                    {opt.label}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">{opt.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Interests */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              <Heart size={14} className="inline mr-1" />
              兴趣偏好（可多选）
            </label>
            <div className="flex flex-wrap gap-2">
              {INTEREST_OPTIONS.map((interest) => (
                <button
                  key={interest.value}
                  type="button"
                  onClick={() => toggleInterest(interest.value)}
                  className={`px-3 py-1.5 rounded-full text-sm transition-all ${
                    form.interests.includes(interest.value)
                      ? "bg-blue-100 text-blue-700 border border-blue-300"
                      : "bg-slate-50 text-slate-600 border border-slate-200 hover:border-slate-300"
                  }`}
                >
                  {interest.label}
                </button>
              ))}
            </div>
          </div>

          {/* Special Requirements */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              特殊需求（选填）
            </label>
            <textarea
              value={form.specialRequirements}
              onChange={(e) => update("specialRequirements", e.target.value)}
              placeholder="例如：素食、无障碍设施、恐高、可携带宠物的酒店……"
              rows={2}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={disabled}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-medium py-3 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:cursor-not-allowed"
          >
            {disabled ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                正在规划……
              </>
            ) : (
              <>
                <Send size={18} />
                开始规划
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
