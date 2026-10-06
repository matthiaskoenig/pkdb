// The value shown where one statistic has to stand for a record: the
// arithmetic mean, else the median, else the geometric mean, else a
// categorical choice. A measured zero is kept; only a missing statistic falls
// through to the next.
export function centralValue<T>(row: Record<string, T>): T | undefined {
  return row.mean ?? row.median ?? row.gmean ?? row.choice;
}
