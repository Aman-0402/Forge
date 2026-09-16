import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireAuth, RequireRole, homeFor } from "./auth/guards";
import AnnouncementsPage from "./pages/AnnouncementsPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import HomePage from "./pages/HomePage";
import Layout from "./pages/Layout";
import LoginPage from "./pages/LoginPage";
import MePage from "./pages/MePage";
import NotificationsPage from "./pages/NotificationsPage";
import RegisterPage from "./pages/RegisterPage";
import ApprovalsPage from "./pages/admin/ApprovalsPage";
import AuditLogPage from "./pages/admin/AuditLogPage";
import CategoriesPage from "./pages/admin/CategoriesPage";
import DepartmentsPage from "./pages/admin/DepartmentsPage";
import UsersPage from "./pages/admin/UsersPage";
import AssignmentPage from "./pages/courses/AssignmentPage";
import CourseFormPage from "./pages/courses/CourseFormPage";
import CoursePage from "./pages/courses/CoursePage";
import CoursesPage from "./pages/courses/CoursesPage";
import MyLearningPage from "./pages/courses/MyLearningPage";
import AttemptResultPage from "./pages/exams/AttemptResultPage";
import BankPage from "./pages/exams/BankPage";
import BanksPage from "./pages/exams/BanksPage";
import ExamFormPage from "./pages/exams/ExamFormPage";
import ExamPage from "./pages/exams/ExamPage";
import ExamsPage from "./pages/exams/ExamsPage";
import MyResultsPage from "./pages/exams/MyResultsPage";
import TakeExamPage from "./pages/exams/TakeExamPage";
import ProblemFormPage from "./pages/coding/ProblemFormPage";
import ProblemsPage from "./pages/coding/ProblemsPage";

// The code editor is large; load it only on pages that use it.
const ProblemPage = lazy(() => import("./pages/coding/ProblemPage"));
const SubmissionPage = lazy(() => import("./pages/coding/SubmissionPage"));
const editorPage = (element: ReactNode) => (
  <Suspense fallback={<p className="hint">Loading editor…</p>}>{element}</Suspense>
);

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <p className="hint">Loading…</p>;
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}

const only = (roles: ("admin" | "faculty" | "student")[], element: ReactNode) => (
  <RequireRole roles={roles}>{element}</RequireRole>
);

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route path="/me" element={<MePage />} />
            <Route path="/change-password" element={<ChangePasswordPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/announcements" element={<AnnouncementsPage />} />
            <Route path="/announcements/:id" element={<AnnouncementsPage />} />

            <Route path="/courses" element={<CoursesPage />} />
            <Route path="/courses/new" element={only(["admin", "faculty"], <CourseFormPage />)} />
            <Route path="/courses/:id" element={<CoursePage />} />
            <Route path="/courses/:id/edit" element={only(["admin", "faculty"], <CourseFormPage />)} />
            <Route path="/courses/:courseId/assignments/:id" element={<AssignmentPage />} />
            <Route path="/assignments/:id" element={<AssignmentPage />} />
            <Route path="/my-learning" element={only(["student"], <MyLearningPage />)} />

            <Route path="/question-banks" element={only(["admin", "faculty"], <BanksPage />)} />
            <Route path="/question-banks/:id" element={only(["admin", "faculty"], <BankPage />)} />
            <Route path="/exams" element={<ExamsPage />} />
            <Route path="/exams/new" element={only(["admin", "faculty"], <ExamFormPage />)} />
            <Route path="/exams/:id" element={<ExamPage />} />
            <Route path="/exams/:id/edit" element={only(["admin", "faculty"], <ExamFormPage />)} />
            <Route path="/attempts/:id/result" element={<AttemptResultPage />} />
            <Route path="/attempts/:id/review" element={only(["admin", "faculty"], <AttemptResultPage review />)} />
            <Route path="/my-results" element={only(["student"], <MyResultsPage />)} />

            <Route path="/problems" element={<ProblemsPage />} />
            <Route path="/problems/new" element={only(["admin", "faculty"], <ProblemFormPage />)} />
            <Route path="/problems/:id" element={editorPage(<ProblemPage />)} />
            <Route path="/problems/:id/edit" element={only(["admin", "faculty"], <ProblemFormPage />)} />
            <Route path="/code-submissions/:id" element={editorPage(<SubmissionPage />)} />

            <Route path="/admin/users" element={only(["admin"], <UsersPage />)} />
            <Route path="/admin/departments" element={only(["admin"], <DepartmentsPage />)} />
            <Route path="/admin/categories" element={only(["admin"], <CategoriesPage />)} />
            <Route path="/admin/approvals" element={only(["admin"], <ApprovalsPage />)} />
            <Route path="/admin/audit-logs" element={only(["admin"], <AuditLogPage />)} />

            {(["admin", "faculty", "student"] as const).map((role) => (
              <Route key={role} path={`/${role}`} element={only([role], <HomePage role={role} />)} />
            ))}
          </Route>
          <Route
            path="/attempts/:id/take"
            element={
              <RequireAuth>
                {only(["student"], <TakeExamPage />)}
              </RequireAuth>
            }
          />
          <Route path="*" element={<p className="page">Page not found.</p>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
