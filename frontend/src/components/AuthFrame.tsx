import type { ReactNode } from "react";

export default function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <div className="auth">
      <section className="auth-art">
        <span className="brand-mark">FORGE</span>
        <div>
          <h2>Courses, exams and code practice in one place.</h2>
          <p>
            Faculty build courses and set assessments. Students learn at their own pace, submit
            work and practise programming with instant feedback.
          </p>
        </div>
        <span className="brand-sub">DSA Forge learning portal</span>
      </section>
      <main className="auth-form">{children}</main>
    </div>
  );
}
