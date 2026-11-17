import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { DataTable, type Column } from "./DataTable";

type Row = { id: string; name: string; risk: number };

const rows: Row[] = [
  { id: "1", name: "Bravo", risk: 40 },
  { id: "2", name: "alpha", risk: 90 },
  { id: "3", name: "Charlie", risk: 5 },
  { id: "4", name: "Delta", risk: 70 },
];

const columns: Column<Row>[] = [
  { key: "name", header: "Name", sortable: true },
  { key: "risk", header: "Risk", sortable: true, align: "right" },
];

function bodyNames() {
  const tbody = screen.getAllByRole("rowgroup")[1];
  return within(tbody)
    .getAllByRole("row")
    .map((r) => within(r).getAllByRole("cell")[0].textContent);
}

describe("DataTable", () => {
  it("sorts ascending, then descending, then back to original order", () => {
    render(<DataTable data={rows} columns={columns} rowKey={(r) => r.id} pageSize={0} />);
    const riskHeader = screen.getByRole("columnheader", { name: /risk/i });
    expect(riskHeader.getAttribute("aria-sort")).toBe("none");

    fireEvent.click(within(riskHeader).getByRole("button"));
    expect(riskHeader.getAttribute("aria-sort")).toBe("ascending");
    expect(bodyNames()).toEqual(["Charlie", "Bravo", "Delta", "alpha"]);

    fireEvent.click(within(riskHeader).getByRole("button"));
    expect(riskHeader.getAttribute("aria-sort")).toBe("descending");
    expect(bodyNames()).toEqual(["alpha", "Delta", "Bravo", "Charlie"]);

    fireEvent.click(within(riskHeader).getByRole("button"));
    expect(bodyNames()).toEqual(["Bravo", "alpha", "Charlie", "Delta"]);
  });

  it("sorts strings case-insensitively", () => {
    render(<DataTable data={rows} columns={columns} rowKey={(r) => r.id} pageSize={0} />);
    fireEvent.click(within(screen.getByRole("columnheader", { name: /name/i })).getByRole("button"));
    expect(bodyNames()).toEqual(["alpha", "Bravo", "Charlie", "Delta"]);
  });

  it("filters rows with the search box and shows an empty state", () => {
    render(<DataTable data={rows} columns={columns} rowKey={(r) => r.id} searchable pageSize={0} />);
    const search = screen.getByRole("searchbox", { name: /search table/i });
    fireEvent.change(search, { target: { value: "ALP" } });
    expect(bodyNames()).toEqual(["alpha"]);
    fireEvent.change(search, { target: { value: "zzz" } });
    expect(screen.getByText(/No matches for/)).toBeTruthy();
  });

  it("paginates", () => {
    render(<DataTable data={rows} columns={columns} rowKey={(r) => r.id} pageSize={3} pageSizeOptions={[3]} />);
    expect(bodyNames()).toHaveLength(3);
    expect(screen.getByText("1–3 of 4")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /next page/i }));
    expect(bodyNames()).toEqual(["Delta"]);
    expect(screen.getByRole("button", { name: /next page/i }).hasAttribute("disabled")).toBe(true);
  });
});
