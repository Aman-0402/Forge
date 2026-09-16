export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type Query = Record<string, string | number | boolean | undefined>;

/** Drop empty values so they are not sent as query params. */
export function cleanQuery(q: Query): Query {
  return Object.fromEntries(Object.entries(q).filter(([, v]) => v !== "" && v !== undefined));
}
