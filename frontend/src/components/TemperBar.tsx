/** Progress bar coloured like tempered steel: cold grey -> straw -> bronze -> purple -> blue. */

const STOPS: [number, [number, number, number]][] = [
  [0, [176, 184, 196]],
  [20, [217, 164, 65]],
  [45, [184, 115, 47]],
  [70, [125, 63, 130]],
  [100, [39, 70, 144]],
];

export function temperColor(percent: number): string {
  const p = Math.max(0, Math.min(100, percent));
  for (let i = 1; i < STOPS.length; i++) {
    const [p1, c1] = STOPS[i];
    const [p0, c0] = STOPS[i - 1];
    if (p <= p1) {
      const t = (p - p0) / (p1 - p0);
      const mix = c0.map((v, k) => Math.round(v + (c1[k] - v) * t));
      return `rgb(${mix.join(", ")})`;
    }
  }
  return "rgb(39, 70, 144)";
}

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
          // width and colour are data-driven; no static class can express them
          style={{ width: `${pct}%`, backgroundColor: temperColor(pct) }}
        />
      </div>
      <span className="temper-value">{pct}%</span>
    </div>
  );
}
