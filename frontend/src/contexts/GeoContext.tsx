import { createContext, useContext, useMemo } from "react";
import { detectGeo, t, type GeoContext as GeoContextType } from "../lib/geo";

interface GeoValue {
  geo: GeoContextType;
  t: typeof t.en;
}

const Ctx = createContext<GeoValue>({
  geo: { lang: "en", country: "US", region: "", isLocal: false, isBrazil: false, regionalData: null },
  t: t.en,
});

export function GeoProvider({ children }: { children: React.ReactNode }) {
  const value = useMemo(() => {
    const geo = detectGeo();
    return { geo, t: geo.lang === "pt" ? t.pt : t.en };
  }, []);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useGeo() {
  return useContext(Ctx);
}
