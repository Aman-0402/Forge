/** Progress bar coloured like tempered steel: cold grey -> straw -> bronze -> purple -> blue. */

export default function TemperBar({
  value,
  large = false,
  label = "Progress",
}: {
  value: number;
  large?: boolean;
  label?: string;
}) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className={large ? "temper lg" : "temper"}>
      <div
        className="temper-track"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
      >
        <div
          className="temper-fill"
          // Data-driven: the gradient is stretched to the full track so the fill shows the
          // temper colours up to this point.
          style={{ width: `${pct}%`, backgroundSize: pct > 0 ? `${10000 / pct}% 100%` : "0 0" }}
        />
      </div>
      <span className="temper-value">{pct}%</span>
    </div>
  );
}
