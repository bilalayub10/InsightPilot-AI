import React, { createContext, useContext, useState } from 'react';
import { AnalyzeResult } from '@workspace/api-client-react';

interface AppState {
  analysisResult: AnalyzeResult | null;
  setAnalysisResult: (res: AnalyzeResult | null) => void;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResult | null>(null);
  return (
    <AppContext.Provider value={{ analysisResult, setAnalysisResult }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppStore() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppStore must be used within AppProvider');
  return ctx;
}
