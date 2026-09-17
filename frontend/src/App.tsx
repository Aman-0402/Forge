import { lazy, Suspense, type ReactNode } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { ThemeProvider } from "./theme/ThemeContext";
import { RequireAuth, RequireRole } from "./auth/guards";
import AnnouncementsPage from "./pages/AnnouncementsPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import HomePage from "./pages/HomePage";
import Layout from "./pages/Layout";
import MePage from "./pages/MePage";
import NotificationsPage from "./pages/NotificationsPage";
import SetPasswordPage from "./pages/SetPasswordPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import MarketingLayout from "./marketing/MarketingLayout";
import PublicHome from "./marketing/pages/PublicHome";
import AnalyticsPage from "./pages/admin/AnalyticsPage";
import ApprovalsPage from "./pages/admin/ApprovalsPage";
import AuditLogPage from "./pages/admin/AuditLogPage";
import CategoriesPage from "./pages/admin/CategoriesPage";
import ContactMessagesPage from "./pages/admin/ContactMessagesPage";
import DepartmentsPage from "./pages/admin/DepartmentsPage";
import MarketingStatsPage from "./pages/admin/MarketingStatsPage";
import SiteSettingsPage from "./pages/admin/SiteSettingsPage";
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

// Public marketing pages (copied from the dsaclone project). Home ships in the main
// bundle since it's what an anonymous visitor sees first; the rest lazy-load.
const Programs = lazy(() => import("./marketing/pages/Programs"));
const MasterClass = lazy(() => import("./marketing/pages/MasterClass"));
const HowWeWork = lazy(() => import("./marketing/pages/HowWeWork"));
const Contact = lazy(() => import("./marketing/pages/Contact"));
const Techies = lazy(() => import("./marketing/pages/Techies"));
const MarketingLogin = lazy(() => import("./marketing/pages/Login"));
const MarketingSignUp = lazy(() => import("./marketing/pages/SignUp"));
const marketingPage = (element: ReactNode) => (
  <Suspense fallback={null}>{element}</Suspense>
);

const only = (roles: ("admin" | "faculty" | "student")[], element: ReactNode) => (
  <RequireRole roles={roles}>{element}</RequireRole>
);

export default function App() {
  return (
    <ThemeProvider>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<MarketingLayout />}>
            <Route path="/" element={<PublicHome />} />
            <Route path="/programs" element={marketingPage(<Programs />)} />
            <Route path="/master-class" element={marketingPage(<MasterClass />)} />
            <Route path="/how-we-work" element={marketingPage(<HowWeWork />)} />
            <Route path="/contact" element={marketingPage(<Contact />)} />
            <Route path="/techies" element={marketingPage(<Techies />)} />
            <Route path="/login" element={marketingPage(<MarketingLogin />)} />
            <Route path="/register" element={marketingPage(<MarketingSignUp />)} />
          </Route>
          <Route path="/set-password" element={<SetPasswordPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
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

            <Route path="/admin/analytics" element={only(["admin"], <AnalyticsPage />)} />
            <Route path="/admin/users" element={only(["admin"], <UsersPage />)} />
            <Route path="/admin/departments" element={only(["admin"], <DepartmentsPage />)} />
            <Route path="/admin/categories" element={only(["admin"], <CategoriesPage />)} />
            <Route path="/admin/approvals" element={only(["admin"], <ApprovalsPage />)} />
            <Route path="/admin/audit-logs" element={only(["admin"], <AuditLogPage />)} />
            <Route path="/admin/contact-messages" element={only(["admin"], <ContactMessagesPage />)} />
            <Route path="/admin/marketing-stats" element={only(["admin"], <MarketingStatsPage />)} />
            <Route path="/admin/settings" element={only(["admin"], <SiteSettingsPage />)} />

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
    </ThemeProvider>
  );
}
