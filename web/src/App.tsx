import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { AuthProvider } from "@/hooks/useAuth";
import { ComparateurPage } from "@/pages/Comparateur";
import { GardeFousPage } from "@/pages/GardeFous";
import { ParcoursPage } from "@/pages/Parcours";
import { StudioPage } from "@/pages/Studio";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<StudioPage />} />
            <Route path="parcours" element={<ParcoursPage />} />
            <Route path="comparateur" element={<ComparateurPage />} />
            <Route path="garde-fous" element={<GardeFousPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
