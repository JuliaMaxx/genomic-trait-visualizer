import { Navigate, Route, Routes } from 'react-router-dom';

import AnalysisPage from '../pages/AnalysisPage';
import LandingPage from '../pages/LandingPage';
import RsidCatalogPage from '../pages/RsidCatalogPage';
import RsidDetailPage from '../pages/RsidDetailPage';
import TraitCatalogPage from '../pages/TraitCatalogPage';
import TraitDetailPage from '../pages/TraitDetailPage';
import TraitAnalysisPage from '../pages/TraitAnalysisPage';

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      <Route path="/analysis" element={<AnalysisPage />} />
      <Route path="/analysis/traits/:traitId" element={<TraitAnalysisPage />} />

      <Route path="/traits" element={<TraitCatalogPage />} />
      <Route path="/traits/:traitId" element={<TraitDetailPage />} />

      <Route path="/rsids" element={<RsidCatalogPage />} />
      <Route path="/rsids/:rsid" element={<RsidDetailPage />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default AppRouter;
