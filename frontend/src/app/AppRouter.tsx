import { Navigate, Route, Routes } from 'react-router-dom';

import AnalysisPage from '../pages/AnalysisPage';
import LandingPage from '../pages/LandingPage';

function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/analysis" element={<AnalysisPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default AppRouter;
