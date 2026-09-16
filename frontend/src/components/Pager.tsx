const PAGE_SIZE = 20;

export default function Pager({
  page,
  count,
  onPage,
}: {
  page: number;
  count: number;
  onPage: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  return (
    <div className="pager">
      <button className="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Previous
      </button>
      <span>
        Page {page} of {pages} · {count} total
      </span>
      <button className="secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Next
      </button>
    </div>
  );
}
