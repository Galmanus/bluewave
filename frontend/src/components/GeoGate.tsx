import { Navigate, Outlet } from "react-router-dom";
import { useGeo } from "../contexts/GeoContext";

/**
 * GeoGate — restricts routes based on geographic location.
 *
 * Usage:
 *   <Route element={<GeoGate blockBrazil />}>
 *     <Route path="/hedera" element={<HederaPage />} />
 *   </Route>
 *
 * Hedera, crypto payments, and DeFi features are only available
 * outside Brazil (regulatory compliance with CVM and Banco Central).
 * Brazilian users see Mercado Pago (PIX, credit card, boleto) instead.
 */

interface GeoGateProps {
  blockBrazil?: boolean;
  redirectTo?: string;
}

export default function GeoGate({ blockBrazil = false, redirectTo = "/billing" }: GeoGateProps) {
  const { geo } = useGeo();

  if (blockBrazil && geo.isBrazil) {
    return <Navigate to={redirectTo} replace />;
  }

  return <Outlet />;
}
