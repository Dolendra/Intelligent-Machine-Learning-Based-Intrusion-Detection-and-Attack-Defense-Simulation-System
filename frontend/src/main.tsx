import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { DetectionPage } from "./pages/DetectionPage";
import { SimulationPage } from "./pages/SimulationPage";
import { ReportsPage } from "./pages/ReportsPage";
import { IncidentDetailPage } from "./pages/IncidentDetailPage";
import { ModelsPage } from "./pages/ModelsPage";
import { CampaignPage } from "./pages/CampaignPage";
import "./styles/global.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/detection" element={<DetectionPage />} />
          <Route path="/simulation" element={<SimulationPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/campaigns" element={<CampaignPage />} />
          <Route path="/campaigns/:campaignId" element={<CampaignPage />} />
          <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
