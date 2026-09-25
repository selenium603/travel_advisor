import { AlertCircle, Clock3, Pencil, RefreshCw, RotateCcw } from "lucide-react";
import { localizeRequest } from "../utils/localizeRequest";
import { hasPastTravelDate } from "../utils/savedRequest";

export default function SavedRequestDetails({ item, error, onRetry, onEdit, onRefresh }) {
  const processing = item.status === "processing";
  const pastDate = hasPastTravelDate(item.request);
  const Icon = processing ? Clock3 : AlertCircle;

  return (
    <div className="mx-4 my-4 max-w-3xl rounded-xl border border-slate-200 bg-white p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <Icon size={22} className={`mt-0.5 shrink-0 ${processing ? "text-blue-600" : "text-red-500"}`} />
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            {processing ? "这条行程仍显示规划中" : "这次行程规划未完成"}
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {processing
              ? "可以刷新查看最新状态。如果长时间没有变化，规划可能已中断，你可以重新提交。"
              : error || "原来的旅行要求已保留，可以直接重试，也可以先修改要求。"}
          </p>
        </div>
      </div>

      <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <h3 className="mb-2 text-sm font-semibold text-slate-700">原旅行要求</h3>
        <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-700">
          {localizeRequest(item.request || "")}
        </p>
      </div>

      {pastDate && (
        <p className="mt-3 text-sm text-amber-700">
          原出发日期已过去，请先修改日期再重新规划。
        </p>
      )}

      <div className="mt-5 flex flex-wrap gap-2">
        {processing && onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw size={16} />刷新状态
          </button>
        )}
        <button
          type="button"
          onClick={onRetry}
          disabled={pastDate || !item.request?.trim()}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          <RotateCcw size={16} />按原要求重试
        </button>
        <button
          type="button"
          onClick={onEdit}
          className="inline-flex items-center gap-2 rounded-lg border border-blue-200 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
        >
          <Pencil size={16} />修改要求
        </button>
      </div>
    </div>
  );
}
