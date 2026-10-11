import { cn } from "@voyara/ui/lib/utils";

export type Column<T> = {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  align?: "start" | "end";
};

type Props<T> = {
  columns: Column<T>[];
  rows: T[] | undefined;
  isLoading?: boolean;
  emptyLabel?: string;
  getRowId: (row: T) => string | number;
};

export function DataTable<T>({
  columns,
  rows,
  isLoading,
  emptyLabel = "Aucune donnée.",
  getRowId,
}: Props<T>) {
  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="bg-muted h-10 animate-pulse rounded" />
        ))}
      </div>
    );
  }

  if (!rows || rows.length === 0) {
    return <p className="text-muted-foreground p-6 text-center text-sm">{emptyLabel}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-muted-foreground border-b text-xs">
            {columns.map((column) => (
              <th
                key={column.key}
                className={cn(
                  "px-4 py-2 font-medium",
                  column.align === "end" ? "text-right" : "text-left",
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={getRowId(row)} className="border-b last:border-0">
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={cn("px-4 py-3", column.align === "end" ? "text-right" : "text-left")}
                >
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
