import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { EmptyState } from "./EmptyState";
import { Skeleton } from "./Skeleton";

export type SortDir = "asc" | "desc";

export interface Column<T> {
  /** Stable column id (also the sort key). */
  key: string;
  header: ReactNode;
  /** Raw value used for sorting and searching. Defaults to `row[key]`. */
  accessor?: (row: T) => unknown;
  /** Custom cell renderer. Defaults to String(accessor(row)). */
  cell?: (row: T) => ReactNode;
  sortable?: boolean;
  /** Include in text search (default true when the table is searchable). */
  searchable?: boolean;
  align?: "left" | "right" | "center";
  width?: string;
  /** Plain-text name for aria (used when header is not a string). */
  ariaLabel?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  rowKey: (row: T, index: number) => string;
  /** Show the search box. */
  searchable?: boolean;
  searchPlaceholder?: string;
  /** Rows per page; 0 disables pagination. Default 10. */
  pageSize?: number;
  pageSizeOptions?: number[];
  initialSort?: { key: string; dir: SortDir };
  /** Extra controls rendered in the toolbar (filters, export…). */
  toolbar?: ReactNode;
  /** Scroll height for the sticky header (e.g. 480 or "60vh"). */
  maxHeight?: number | string;
  emptyTitle?: string;
  emptyDescription?: ReactNode;
  loading?: boolean;
  dense?: boolean;
  caption?: string;
  onRowClick?: (row: T) => void;
}

function defaultAccessor<T>(col: Column<T>) {
  return col.accessor ?? ((row: T) => (row as Record<string, unknown>)[col.key]);
}

function compare(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0;
  if (a == null || a === "") return 1;
  if (b == null || b === "") return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  if (typeof a === "boolean" && typeof b === "boolean") return Number(a) - Number(b);
  const na = Number(a);
  const nb = Number(b);
  if (typeof a === "string" && typeof b === "string" && a.trim() !== "" && b.trim() !== "" && !Number.isNaN(na) && !Number.isNaN(nb)) {
    return na - nb;
  }
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

/** Sortable, searchable, paginated table with a sticky header. Sorting/search run on `accessor` values. */
export function DataTable<T>({
  data,
  columns,
  rowKey,
  searchable = false,
  searchPlaceholder = "Search…",
  pageSize = 10,
  pageSizeOptions = [10, 25, 50],
  initialSort,
  toolbar,
  maxHeight,
  emptyTitle = "No rows",
  emptyDescription,
  loading,
  dense,
  caption,
  onRowClick,
}: DataTableProps<T>) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: string; dir: SortDir } | null>(initialSort ?? null);
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(pageSize);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return data;
    const cols = columns.filter((c) => c.searchable !== false);
    return data.filter((row) =>
      cols.some((c) => {
        const v = defaultAccessor(c)(row);
        return v != null && String(v).toLowerCase().includes(q);
      })
    );
  }, [data, columns, query]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const col = columns.find((c) => c.key === sort.key);
    if (!col) return filtered;
    const get = defaultAccessor(col);
    const mul = sort.dir === "asc" ? 1 : -1;
    return filtered
      .map((row, i) => ({ row, i }))
      .sort((a, b) => compare(get(a.row), get(b.row)) * mul || a.i - b.i)
      .map((x) => x.row);
  }, [filtered, sort, columns]);

  const pages = size > 0 ? Math.max(1, Math.ceil(sorted.length / size)) : 1;
  useEffect(() => {
    if (page > pages - 1) setPage(pages - 1);
  }, [page, pages]);
  const visible = size > 0 ? sorted.slice(page * size, page * size + size) : sorted;

  function toggleSort(key: string) {
    setPage(0);
    setSort((cur) => {
      if (!cur || cur.key !== key) return { key, dir: "asc" };
      if (cur.dir === "asc") return { key, dir: "desc" };
      return null;
    });
  }

  const showToolbar = searchable || toolbar;

  return (
    <div className="datatable">
      {showToolbar && (
        <div className="dt-toolbar">
          {searchable && (
            <label className="input-with-icon dt-search">
              <Search size={15} aria-hidden />
              <span className="sr-only">Search table</span>
              <input
                className="input input-sm"
                type="search"
                value={query}
                placeholder={searchPlaceholder}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setPage(0);
                }}
              />
            </label>
          )}
          {toolbar}
        </div>
      )}

      <div className="table-wrap" style={maxHeight != null ? { maxHeight } : undefined}>
        <table className={`table${dense ? " dense" : ""}`}>
          {caption ? <caption className="sr-only">{caption}</caption> : null}
          <thead>
            <tr>
              {columns.map((c) => {
                const active = sort?.key === c.key;
                const ariaSort = active ? (sort!.dir === "asc" ? "ascending" : "descending") : c.sortable ? "none" : undefined;
                const SortIcon = !active ? ArrowUpDown : sort!.dir === "asc" ? ArrowUp : ArrowDown;
                return (
                  <th
                    key={c.key}
                    scope="col"
                    aria-sort={ariaSort}
                    style={{ width: c.width, textAlign: c.align ?? "left" }}
                  >
                    {c.sortable ? (
                      <button type="button" className="sort-btn" onClick={() => toggleSort(c.key)}>
                        {c.header}
                        <SortIcon size={12} aria-hidden style={{ opacity: active ? 1 : 0.45 }} />
                      </button>
                    ) : (
                      c.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: Math.min(size || 5, 5) }, (_, i) => (
                  <tr key={`sk-${i}`}>
                    {columns.map((c) => (
                      <td key={c.key}>
                        <Skeleton width="70%" />
                      </td>
                    ))}
                  </tr>
                ))
              : visible.map((row, i) => (
                  <tr
                    key={rowKey(row, i)}
                    data-clickable={onRowClick ? "true" : undefined}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                  >
                    {columns.map((c) => (
                      <td key={c.key} className={c.align === "right" ? "num" : c.align === "center" ? "center" : undefined}>
                        {c.cell ? c.cell(row) : String(defaultAccessor(c)(row) ?? "—")}
                      </td>
                    ))}
                  </tr>
                ))}
          </tbody>
        </table>
        {!loading && visible.length === 0 && (
          <div style={{ padding: 12 }}>
            <EmptyState
              compact
              title={query ? `No matches for “${query}”` : emptyTitle}
              description={query ? "Try a different search term." : emptyDescription}
            />
          </div>
        )}
      </div>

      {size > 0 && sorted.length > 0 && (
        <div className="dt-footer">
          <span aria-live="polite">
            {sorted.length === 0 ? 0 : page * size + 1}–{Math.min(sorted.length, (page + 1) * size)} of {sorted.length}
            {query ? ` (filtered from ${data.length})` : ""}
          </span>
          <div className="row" style={{ gap: 6 }}>
            {pageSizeOptions.length > 1 && (
              <label className="row" style={{ gap: 6 }}>
                <span>Rows</span>
                <select
                  className="select select-sm"
                  style={{ width: 74 }}
                  value={size}
                  onChange={(e) => {
                    setSize(Number(e.target.value));
                    setPage(0);
                  }}
                >
                  {pageSizeOptions.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <button
              type="button"
              className="btn btn-secondary btn-icon btn-sm"
              aria-label="Previous page"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              <ChevronLeft size={15} />
            </button>
            <span className="mono">
              {page + 1}/{pages}
            </span>
            <button
              type="button"
              className="btn btn-secondary btn-icon btn-sm"
              aria-label="Next page"
              disabled={page >= pages - 1}
              onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
            >
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
