import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getReportsOverview, type CountRow } from "../../api/admin";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../utils/format";

// A fixed categorical palette, deliberately not theme-driven — chart data colours
// stay the same in light and dark mode; only the chrome around them (axes, grid,
// legend, tooltip) reads from the app's CSS variables below.
const PALETTE = ["#2f6fed", "#22c55e", "#f59e0b", "#a855f7", "#ef4444", "#06b6d4", "#84cc16", "#ec4899"];

const AXIS_TICK = { fill: "var(--ink-3)", fontSize: 11 };
const TOOLTIP_STYLE = {
  background: "var(--surface)",
  border: "1px solid var(--line)",
  borderRadius: "var(--radius)",
  color: "var(--ink)",
  fontSize: "0.85rem",
};
const LEGEND_STYLE = { fontSize: "0.8rem", color: "var(--ink-2)" };

function titleCase(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="panel chart-card">
      <div className="panel-head">
        <h2>{title}</h2>
        {subtitle && <span className="hint">{subtitle}</span>}
      </div>
      {children}
    </div>
  );
}

function DonutCard({ title, rows, total }: { title: string; rows: CountRow[]; total?: number }) {
  if (!rows.length) {
    return (
      <ChartCard title={title}>
        <p className="empty">No data yet.</p>
      </ChartCard>
    );
  }
  return (
    <ChartCard title={title} subtitle={total ? `${total} total` : undefined}>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie data={rows} dataKey="count" nameKey="label" innerRadius={48} outerRadius={80} paddingAngle={2}>
            {rows.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v, n) => [String(v), titleCase(String(n))]} />
          <Legend wrapperStyle={LEGEND_STYLE} formatter={(v) => titleCase(String(v))} />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export default function AnalyticsPage() {
  const report = useLoad(getReportsOverview, []);
  const data = report.data;

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Administration</div>
          <h1>Analytics</h1>
        </div>
        {data && <span className="hint">Generated {formatDate(data.generated_at)}</span>}
      </div>
      {report.error && <p className="error">{report.error}</p>}
      {report.loading && <p className="hint">Loading…</p>}
      {!data ? null : (
        <>
          <div className="stat-row">
            <div className="stat">
              <div className="stat-value">{data.users_by_role.reduce((n, r) => n + r.count, 0)}</div>
              <div className="stat-label">Total users</div>
            </div>
            <div className="stat">
              <div className="stat-value">{data.users_active.active}</div>
              <div className="stat-label">Active users</div>
            </div>
            <div className="stat">
              <div className="stat-value">{data.courses_by_status.reduce((n, r) => n + r.count, 0)}</div>
              <div className="stat-label">Total courses</div>
            </div>
            <div className="stat">
              <div className="stat-value">
                {data.exam_pass_fail.passed + data.exam_pass_fail.failed + data.exam_pass_fail.ungraded}
              </div>
              <div className="stat-label">Exam attempts</div>
            </div>
            <div className="stat">
              <div className="stat-value">
                {data.coding_submissions_by_verdict.reduce((n, r) => n + r.count, 0)}
              </div>
              <div className="stat-label">Code submissions</div>
            </div>
            <div className="stat">
              <div className="stat-value">{data.contact_messages_total}</div>
              <div className="stat-label">Contact messages</div>
            </div>
          </div>

          <div className="chart-grid">
            <DonutCard
              title="Users by role"
              rows={data.users_by_role}
              total={data.users_by_role.reduce((n, r) => n + r.count, 0)}
            />
            <DonutCard title="Courses by status" rows={data.courses_by_status} />
            <DonutCard title="Enrollments by status" rows={data.enrollments_by_status} />
            <DonutCard
              title="Exam results"
              rows={[
                { label: "passed", count: data.exam_pass_fail.passed },
                { label: "failed", count: data.exam_pass_fail.failed },
                { label: "ungraded", count: data.exam_pass_fail.ungraded },
              ].filter((r) => r.count > 0)}
            />
            <DonutCard title="Problems by difficulty" rows={data.problems_by_difficulty} />

            <ChartCard title="Code submissions by verdict">
              {data.coding_submissions_by_verdict.length === 0 ? (
                <p className="empty">No judged submissions yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={data.coding_submissions_by_verdict} layout="vertical" margin={{ left: 24 }}>
                    <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} tick={AXIS_TICK} />
                    <YAxis
                      type="category"
                      dataKey="label"
                      width={110}
                      tickFormatter={titleCase}
                      tick={AXIS_TICK}
                    />
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      formatter={(v) => [String(v), "Submissions"]}
                      labelFormatter={(l) => titleCase(String(l))}
                    />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                      {data.coding_submissions_by_verdict.map((_, i) => (
                        <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </ChartCard>

            <ChartCard title="Top courses by active enrollment" subtitle="up to 8">
              {data.top_courses_by_enrollment.length === 0 ? (
                <p className="empty">No active enrollments yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={data.top_courses_by_enrollment}>
                    <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="code" tick={AXIS_TICK} />
                    <YAxis allowDecimals={false} tick={AXIS_TICK} />
                    <Tooltip
                      contentStyle={TOOLTIP_STYLE}
                      formatter={(v) => [String(v), "Enrolled"]}
                      labelFormatter={(code, payload) => String(payload?.[0]?.payload?.course ?? code)}
                    />
                    <Bar dataKey="count" fill={PALETTE[0]} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </ChartCard>
          </div>
        </>
      )}
    </>
  );
}
