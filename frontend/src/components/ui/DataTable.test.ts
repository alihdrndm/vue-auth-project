import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, ref } from "vue";

import DataTable, {
  type DataTableColumn,
  type DataTableSort,
} from "./DataTable.vue";

interface Row {
  id: string;
  supplier: string;
  gross: string;
}

const COLUMNS: DataTableColumn<Row>[] = [
  {
    key: "supplier",
    label: "Supplier",
    sortable: true,
    value: (r) => r.supplier,
  },
  { key: "number", label: "Number" },
  {
    key: "gross",
    label: "Gross",
    sortable: true,
    align: "right",
    mono: true,
    value: (r) => r.gross,
  },
];

const ROWS: Row[] = [
  { id: "1", supplier: "Elektro Kessler GmbH", gross: "1.190,00 €" },
  { id: "2", supplier: "Bürobedarf Nord KG", gross: "412,34 €" },
];

interface Options {
  rows?: Row[];
  sort?: DataTableSort | null;
  selectedKeys?: string[];
}

// A typed host, so the table's row type is inferred as Row.
function mountTable(options: Options = {}) {
  const sort = ref<DataTableSort | null>(options.sort ?? null);
  const Host = defineComponent({
    setup: () => () =>
      h(
        DataTable<Row>,
        {
          caption: "Invoices",
          columns: COLUMNS,
          rows: options.rows ?? ROWS,
          rowKey: (row: Row) => row.id,
          selectedKeys: options.selectedKeys,
          sort: sort.value,
          "onUpdate:sort": (value: DataTableSort | null) => {
            sort.value = value;
          },
        },
        {
          "cell-number": ({ row }: { row: Row }) => `N-${row.id}`,
          empty: () => h("p", "Nothing needs review"),
        },
      ),
  });
  const wrapper = mount(Host);
  return { wrapper, table: wrapper.findComponent(DataTable), sort };
}

describe("DataTable", () => {
  it("renders a real table with a caption and header cells", () => {
    const { wrapper } = mountTable();
    expect(wrapper.get("caption").text()).toBe("Invoices");
    const headers = wrapper.findAll("th");
    expect(headers.map((th) => th.text())).toEqual([
      "Supplier",
      "Number",
      "Gross",
    ]);
    expect(headers.every((th) => th.attributes("scope") === "col")).toBe(true);
    const cells = wrapper.findAll("tbody tr")[0]?.findAll("td") ?? [];
    expect(cells.map((c) => c.text())).toEqual([
      "Elektro Kessler GmbH",
      "N-1",
      "1.190,00 €",
    ]);
    expect(cells[2]?.classes()).toEqual(
      expect.arrayContaining(["is-right", "is-mono"]),
    );
  });

  it("exposes sort state with aria-sort and toggles it from the header button", async () => {
    const { wrapper, sort } = mountTable();
    const headers = () => wrapper.findAll("th");
    expect(headers()[0]?.attributes("aria-sort")).toBe("none");
    expect(headers()[1]?.attributes("aria-sort")).toBeUndefined();
    expect(headers()[1]?.find("button").exists()).toBe(false);

    await headers()[0]?.get("button").trigger("click");
    expect(sort.value).toEqual({ key: "supplier", direction: "ascending" });
    expect(headers()[0]?.attributes("aria-sort")).toBe("ascending");

    await headers()[0]?.get("button").trigger("click");
    expect(sort.value).toEqual({ key: "supplier", direction: "descending" });
    expect(headers()[0]?.attributes("aria-sort")).toBe("descending");

    await headers()[2]?.get("button").trigger("click");
    expect(sort.value).toEqual({ key: "gross", direction: "ascending" });
    expect(headers()[0]?.attributes("aria-sort")).toBe("none");
  });

  it("opens a row by click and by keyboard", async () => {
    const { wrapper, table } = mountTable();
    const row = wrapper.findAll("tbody tr")[1];
    expect(row?.attributes("tabindex")).toBe("0");
    await row?.trigger("click");
    await row?.trigger("keydown", { key: "Enter" });
    await row?.trigger("keydown", { key: " " });
    await row?.trigger("keydown", { key: "a" });
    const emitted = table.emitted("row-click") ?? [];
    expect(emitted).toHaveLength(3);
    expect(emitted[0]).toEqual([ROWS[1]]);
  });

  it("marks selected rows", () => {
    const { wrapper } = mountTable({ selectedKeys: ["2"] });
    const rows = wrapper.findAll("tbody tr");
    expect(rows[0]?.attributes("aria-selected")).toBe("false");
    expect(rows[1]?.attributes("aria-selected")).toBe("true");
  });

  it("shows the empty slot when there are no rows", () => {
    const { wrapper } = mountTable({ rows: [] });
    expect(wrapper.findAll("tbody tr")).toHaveLength(0);
    expect(wrapper.text()).toContain("Nothing needs review");
  });

  it("hides the empty slot when there are rows", () => {
    const { wrapper } = mountTable();
    expect(wrapper.text()).not.toContain("Nothing needs review");
  });
});
