const KEY = "travel-planner-session-id";

export function getSessionId() {
  let id = sessionStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(KEY, id);
  }
  return id;
}

export function profileBudgetToForm(value = "") {
  const text = value.toLowerCase();
  if (text.includes("ultra-luxury") || text.includes("奢华") || text.includes("顶级")) return "ultra-luxury";
  if (text.includes("luxury") || text.includes("豪华")) return "luxury";
  if (text.includes("budget") || text.includes("经济") || text.includes("省钱")) return "budget";
  if (text.includes("mid-range") || text.includes("中等") || text.includes("适中")) return "mid-range";
  return null;
}
