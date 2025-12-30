import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './contexts/AppContext';
import { HomePage, GraphPage, MyLearningPage } from './pages';

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-[#FAFAFA] text-zinc-900 font-sans selection:bg-zinc-200 selection:text-zinc-900 antialiased overflow-hidden">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/graph/:planId" element={<GraphPage />} />
            <Route path="/my-learning" element={<MyLearningPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </BrowserRouter>
    </AppProvider>
  );
}
