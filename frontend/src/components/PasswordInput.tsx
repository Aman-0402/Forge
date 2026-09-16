import { useState, type InputHTMLAttributes } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type">;

export default function PasswordInput(props: Props) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="password-field">
      <input {...props} type={visible ? "text" : "password"} />
      <button
        type="button"
        className="eye-button"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? "Hide password" : "Show password"}
        aria-pressed={visible}
        title={visible ? "Hide password" : "Show password"}
      >
        {visible ? <EyeOffIcon /> : <EyeIcon />}
      </button>
    </div>
  );
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path
        d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      />
      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path
        d="M17.9 17.9A10.8 10.8 0 0 1 12 19C5 19 1 12 1 12a19.8 19.8 0 0 1 5.1-5.9M9.9 5.2A9.9 9.9 0 0 1 12 5c7 0 11 7 11 7a19.9 19.9 0 0 1-2.2 3.2M14.1 14.1a3 3 0 1 1-4.2-4.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      />
      <line x1="1" y1="1" x2="23" y2="23" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}
