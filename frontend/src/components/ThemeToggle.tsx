import { useTheme, type ThemePreference } from "../theme/ThemeContext";

const OPTIONS: { value: ThemePreference; label: string; icon: string }[] = [
  { value: "light", label: "Light", icon: "☀" },
  { value: "dark", label: "Dark", icon: "☾" },
  { value: "system", label: "Auto", icon: "◐" },
];

/** Three-way theme switch for the sidebar. Dark mode matches the public site's
 * gold-on-black look (see index.css); "Auto" follows the OS setting. */
export default function ThemeToggle() {
  const { preference, setPreference } = useTheme();

  return (
    <div className="theme-toggle" role="radiogroup" aria-label="Theme">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="radio"
          aria-checked={preference === opt.value}
          className={preference === opt.value ? "active" : ""}
          onClick={() => setPreference(opt.value)}
          title={opt.label}
        >
          <span aria-hidden="true">{opt.icon}</span>
          {opt.label}
        </button>
      ))}
    </div>
  );
}
