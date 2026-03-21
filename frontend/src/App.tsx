import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider } from "./contexts/AuthContext";
import { GeoProvider } from "./contexts/GeoContext";
import AuthGuard from "./components/AuthGuard";
import RoleGuard from "./components/RoleGuard";
import GeoGate from "./components/GeoGate";
import AppLayout from "./components/AppLayout";

// Eagerly loaded (part of initial bundle)
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

// Lazy loaded (code-split into separate chunks)
const AssetListPage = lazy(() => import("./pages/AssetListPage"));
const AssetDetailPage = lazy(() => import("./pages/AssetDetailPage"));
const UploadPage = lazy(() => import("./pages/UploadPage"));
const TeamPage = lazy(() => import("./pages/TeamPage"));
const IntegrationsPage = lazy(() => import("./pages/IntegrationsPage"));
const TrendsPage = lazy(() => import("./pages/TrendsPage"));
const BrandPage = lazy(() => import("./pages/BrandPage"));
const BillingPage = lazy(() => import("./pages/BillingPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const BriefsPage = lazy(() => import("./pages/BriefsPage"));
const WaveAgentPage = lazy(() => import("./pages/WaveAgentPage"));
const BrandDNAPage = lazy(() => import("./pages/BrandDNAPage"));
const HederaPage = lazy(() => import("./pages/HederaPage"));

const queryClient = new QueryClient();

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <GeoProvider>
        <AuthProvider>
          <BrowserRouter>
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route element={<AuthGuard />}>
                  <Route element={<AppLayout />}>
                    <Route path="/assets" element={<AssetListPage />} />
                    <Route path="/assets/:id" element={<AssetDetailPage />} />
                    <Route element={<RoleGuard role="editor" />}>
                      <Route path="/assets/upload" element={<UploadPage />} />
                      <Route path="/trends" element={<TrendsPage />} />
                      <Route path="/calendar" element={<CalendarPage />} />
                      <Route path="/briefs" element={<BriefsPage />} />
                      <Route path="/wave" element={<WaveAgentPage />} />
                    </Route>
                    <Route element={<RoleGuard role="admin" />}>
                      <Route path="/team" element={<TeamPage />} />
                      <Route path="/brand" element={<BrandPage />} />
                      <Route path="/brand-dna" element={<BrandDNAPage />} />
                      <Route path="/integrations" element={<IntegrationsPage />} />
                      <Route path="/billing" element={<BillingPage />} />
                      <Route path="/analytics" element={<AnalyticsPage />} />
                      {/* Hedera/crypto only available outside Brazil (regulatory compliance) */}
                      <Route element={<GeoGate blockBrazil />}>
                        <Route path="/hedera" element={<HederaPage />} />
                      </Route>
                    </Route>
                  </Route>
                </Route>
              </Routes>
            </Suspense>
          </BrowserRouter>
        </AuthProvider>
        <Toaster
          position="bottom-right"
          toastOptions={{ duration: 4000 }}
          theme="system"
          richColors
        />
      </GeoProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
