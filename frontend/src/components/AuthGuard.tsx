import { Navigate, Outlet } from "react-router-dom";
import { Waves } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

export default function AuthGuard() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <Waves className="h-8 w-8 text-accent animate-pulse" />
          <div className="h-1 w-24 overflow-hidden rounded-full bg-border">
            <div className="h-full w-1/2 animate-[slideInRight_1s_ease-in-out_infinite] rounded-full bg-accent" />
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
