"use client";

export function TableSkeleton() {
  return (
    <div className="panel" style={{ padding: "20px 24px" }}>
      <div
        className="skeleton"
        style={{ width: 120, height: 10, marginBottom: 20, borderRadius: 4 }}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} style={{ display: "flex", gap: 16 }}>
            <div
              className="skeleton"
              style={{ width: `${60 + (i % 3) * 20}px`, height: 10, borderRadius: 4 }}
            />
            <div className="skeleton" style={{ flex: 1, height: 10, borderRadius: 4 }} />
            <div className="skeleton" style={{ width: 60, height: 10, borderRadius: 4 }} />
            <div className="skeleton" style={{ width: 40, height: 10, borderRadius: 4 }} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function KpiSkeleton() {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(5, 1fr)",
        gap: 12,
        marginBottom: 12,
      }}
    >
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="panel" style={{ padding: "20px 24px" }}>
          <div
            className="skeleton"
            style={{ width: "60%", height: 28, borderRadius: 4, marginBottom: 10 }}
          />
          <div className="skeleton" style={{ width: "80%", height: 8, borderRadius: 4 }} />
        </div>
      ))}
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <KpiSkeleton />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <TableSkeleton />
        <TableSkeleton />
      </div>
      <TableSkeleton />
    </div>
  );
}

export function InsightSkeleton() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
      {Array.from({ length: 3 }).map((_, col) => (
        <div key={col}>
          <div
            className="skeleton"
            style={{ width: 80, height: 8, borderRadius: 4, marginBottom: 16 }}
          />
          {Array.from({ length: 4 }).map((_, row) => (
            <div
              key={row}
              className="panel"
              style={{
                padding: "14px 16px",
                marginBottom: 8,
                borderLeft: "2px solid var(--border)",
              }}
            >
              <div
                className="skeleton"
                style={{ width: "100%", height: 8, borderRadius: 4, marginBottom: 6 }}
              />
              <div
                className="skeleton"
                style={{ width: "70%", height: 8, borderRadius: 4 }}
              />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
