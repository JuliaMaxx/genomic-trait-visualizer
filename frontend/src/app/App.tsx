import { BrowserRouter } from 'react-router-dom';
import AppShell from '../components/AppShell';
import { AnalysisSessionProvider } from '../context/AnalysisSessionProvider';
import AppRouter from './AppRouter';

function App() {
  return (
    <BrowserRouter>
      <AnalysisSessionProvider>
        <AppShell>
          <AppRouter />
        </AppShell>
      </AnalysisSessionProvider>
    </BrowserRouter>
  );
}

export default App;
