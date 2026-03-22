"use client";

import { memo, useMemo } from "react";
import { BudgetCategory, BudgetSummary } from "@/lib/types";

interface BudgetChartProps {
  data: BudgetSummary;
}

// Category display config: label, color
const categoryConfig: Record<
  BudgetCategory,
  { label: string; color: string; bgClass: string; textClass: string }
> = {
  transport: {
    label: "交通",
    color: "#0ea5e9",
    bgClass: "bg-sky-500",
    textClass: "text-sky-500",
  },
  accommodation: {
    label: "住宿",
    color: "#8b5cf6",
    bgClass: "bg-purple-500",
    textClass: "text-purple-500",
  },
  food: {
    label: "餐饮",
    color: "#f97316",
    bgClass: "bg-orange-500",
    textClass: "text-orange-500",
  },
  ticket: {
    label: "门票",
    color: "#22c55e",
    bgClass: "bg-green-500",
    textClass: "text-green-500",
  },
  other: {
    label: "其他",
    color: "#64748b",
    bgClass: "bg-slate-500",
    textClass: "text-slate-500",
  },
};

/**
 * Aggregated category data for chart rendering.
 */
interface CategoryAgg {
  category: BudgetCategory;
  label: string;
  amount: number;
  percentage: number;
  color: string;
  bgClass: string;
  textClass: string;
}

/**
 * Budget visualization: horizontal bar chart + detail table.
 * Pure CSS implementation, no external chart libraries.
 */
export default memo(function BudgetChart({ data }: BudgetChartProps) {
  // Aggregate items by category
  const categories = useMemo<CategoryAgg[]>(() => {
    const map = new Map<BudgetCategory, number>();
    for (const item of data.items) {
      map.set(item.category, (map.get(item.category) || 0) + item.amount);
    }

    const total = data.totalSpent || 1;
    const result: CategoryAgg[] = [];
    for (const [cat, amount] of map.entries()) {
      const cfg = categoryConfig[cat];
      result.push({
        category: cat,
        label: cfg.label,
        amount,
        percentage: Math.round((amount / total) * 100),
        color: cfg.color,
        bgClass: cfg.bgClass,
        textClass: cfg.textClass,
      });
    }

    // Sort descending by amount
    result.sort((a, b) => b.amount - a.amount);
    return result;
  }, [data]);

  const usagePercent = Math.round(
    (data.totalSpent / data.totalBudget) * 100
  );

  return (
    <div className="space-y-6">
      {/* Overall budget bar */}
      <div className="bg-surface-container-high ghost-border rounded-xl p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-medium text-on-surface">
            总预算使用
          </span>
          <span className="text-sm text-on-surface-variant">
            {usagePercent}%
          </span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-surface-container-highest">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{ width: `${Math.min(usagePercent, 100)}%` }}
          />
        </div>
        <div className="mt-2 flex items-center justify-between text-xs text-on-surface-variant">
          <span>
            已用{" "}
            <span className="text-primary font-semibold">
              {data.currency} {data.totalSpent.toLocaleString()}
            </span>
          </span>
          <span>
            预算{" "}
            <span className="font-semibold text-on-surface">
              {data.currency} {data.totalBudget.toLocaleString()}
            </span>
          </span>
        </div>
      </div>

      {/* Category breakdown - horizontal bar chart */}
      <div className="bg-surface-container-high ghost-border rounded-xl p-4">
        <h4 className="mb-4 text-sm font-semibold text-on-surface">
          分类占比
        </h4>

        {/* Stacked bar */}
        <div className="mb-4 flex h-6 w-full overflow-hidden rounded-full">
          {categories.map((cat) => (
            <div
              key={cat.category}
              className={`${cat.bgClass} transition-all duration-500`}
              style={{ width: `${cat.percentage}%` }}
              title={`${cat.label}: ${cat.percentage}%`}
            />
          ))}
        </div>

        {/* Legend + per-category bars */}
        <div className="space-y-3">
          {categories.map((cat) => (
            <div key={cat.category} className="flex items-center gap-2 sm:gap-3">
              <div
                className={`h-3 w-3 shrink-0 rounded-full ${cat.bgClass}`}
              />
              <span className="w-8 shrink-0 text-xs font-medium text-on-surface sm:w-10">
                {cat.label}
              </span>
              <div className="flex-1 min-w-0">
                <div className="h-2 w-full overflow-hidden rounded-full bg-surface-container-highest">
                  <div
                    className={`h-full rounded-full ${cat.bgClass} transition-all duration-500`}
                    style={{ width: `${cat.percentage}%` }}
                  />
                </div>
              </div>
              <span className="hidden shrink-0 text-right text-xs text-on-surface-variant sm:inline w-20">
                {data.currency} {cat.amount.toLocaleString()}
              </span>
              <span className="w-10 shrink-0 text-right text-xs font-medium text-on-surface">
                {cat.percentage}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Detail table */}
      <div className="bg-surface-container-high ghost-border rounded-xl">
        <div className="border-b border-outline-variant/30 p-4">
          <h4 className="text-sm font-semibold text-on-surface">
            明细清单
          </h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-outline-variant/30 text-left text-xs text-on-surface-variant">
                <th className="px-2.5 py-2 font-medium sm:px-4 sm:py-3">项目</th>
                <th className="px-2.5 py-2 font-medium sm:px-4 sm:py-3">分类</th>
                <th className="hidden px-4 py-3 font-medium sm:table-cell">
                  备注
                </th>
                <th className="px-2.5 py-2 text-right font-medium sm:px-4 sm:py-3">金额</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => {
                const cfg = categoryConfig[item.category];
                return (
                  <tr
                    key={item.id}
                    className="border-b border-outline-variant/20 last:border-b-0"
                  >
                    <td className="max-w-[120px] truncate px-2.5 py-2 text-on-surface sm:max-w-none sm:px-4 sm:py-3">
                      {item.name}
                    </td>
                    <td className="px-2.5 py-2 sm:px-4 sm:py-3">
                      <span
                        className={`inline-flex items-center gap-1 text-xs ${cfg.textClass}`}
                      >
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${cfg.bgClass}`}
                        />
                        {cfg.label}
                      </span>
                    </td>
                    <td className="hidden px-4 py-3 text-xs text-on-surface-variant sm:table-cell">
                      {item.note || "-"}
                    </td>
                    <td className="whitespace-nowrap px-2.5 py-2 text-right font-medium text-on-surface sm:px-4 sm:py-3">
                      {item.currency} {item.amount.toLocaleString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {/* Footer total */}
        <div className="flex items-center justify-between border-t border-outline-variant/30 px-4 py-3">
          <span className="text-sm font-medium text-on-surface">
            合计
          </span>
          <span className="text-sm text-primary font-semibold">
            {data.currency} {data.totalSpent.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
});
