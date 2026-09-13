export function pageNumber(value?: string) {
  return Math.max(1, Number.parseInt(value ?? "1", 10) || 1);
}

export function pageOffset(page: number, limit: number) {
  return (Math.max(1, page) - 1) * limit;
}

export function hasNextPage(itemCount: number, limit: number) {
  return itemCount === limit;
}

export function pollingDelay(failures: number, normalMs: number) {
  return failures > 0 ? 30_000 : normalMs;
}
