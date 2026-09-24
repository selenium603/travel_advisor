const LABELS = {
  "Trip Request": "旅行想法",
  "Essential Details": "行程信息",
  "Travel Dates": "出行日期",
  "Departure City": "出发城市",
  "Number of Travelers": "出行人数",
  "Traveler Details": "同行人说明",
  "Budget Level": "预算档次",
  Interests: "兴趣偏好",
  "Special Requirements": "特殊需求",
};

const VALUES = {
  budget: "经济型",
  "mid-range": "舒适型",
  luxury: "豪华型",
  "ultra-luxury": "奢华型",
  "Food & Cuisine": "美食",
  "History & Culture": "历史文化",
  "Art & Museums": "艺术与博物馆",
  "Adventure & Outdoors": "户外探险",
  "Beaches & Relaxation": "海滩休闲",
  Nightlife: "夜生活",
  Shopping: "购物",
  Architecture: "建筑",
  "Nature & Wildlife": "自然与野生动物",
  Photography: "摄影",
  "Wine & Spirits": "葡萄酒与烈酒",
  "Family Fun": "亲子活动",
};

export function localizeRequest(request = "") {
  return request.split(/\r?\n/).map((line) => {
    const match = line.match(/^(\s*-?\s*)([^:]+):\s*(.*)$/);
    if (!match || !LABELS[match[2]]) return line;
    const [, prefix, field, rawValue] = match;
    let value = rawValue;
    if (field === "Travel Dates") {
      value = value.replace(/\s+to\s+/i, " 至 ").replace(/\s*\((\d+) days?\)/i, "（$1 天）");
    } else if (field === "Number of Travelers") {
      value = `${value} 人`;
    } else if (field === "Interests") {
      value = value.split(/,\s*/).map((item) => VALUES[item] || item).join("、");
    } else {
      value = VALUES[value] || value;
    }
    return `${prefix}${LABELS[field]}：${value}`;
  }).join("\n");
}
