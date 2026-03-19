import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const ROLE_HIERARCHY: Record<string, number> = {
  viewer: 0,
  editor: 1,
  admin: 2,
};

interface RoleGuardProps {
  role: string;
}

export default function RoleGuard({ role }: RoleGuardProps) {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;

  const userLevel = ROLE_HIERARCHY[user.role] ?? -1;
  const requiredLevel = ROLE_HIERARCHY[role] ?? 99;

  if (userLevel < requiredLevel) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
