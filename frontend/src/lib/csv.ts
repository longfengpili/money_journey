export function makeCsv(rows: (string | number)[][]) {
  return (
    "\ufeff" +
    rows
      .map((row) =>
        row
          .map((value) => '"' + String(value).replaceAll('"', '""') + '"')
          .join(","),
      )
      .join("\r\n")
  );
}

export function downloadCsv(name: string, rows: (string | number)[][]) {
  const url = URL.createObjectURL(
    new Blob([makeCsv(rows)], { type: "text/csv;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
