import React, { Suspense } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppProviders } from "./app/AppProviders";
import { APP_ROUTES, lazyPage } from "./app/routes";
import { AppLayout } from "./components/AppLayout";
import { PageSkeleton } from "./components/ui/Skeleton";
import "./styles/global.css";
import "./styles/v3.css";

const LoginPage = lazyPage(() => import("./pages/LoginPage"), "LoginPage");
const NotFoundPage = lazyPage(() => import("./pages/NotFoundPage"), "NotFoundPage");

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppProviders>
        <Routes>
          <Route
            path="/login"
            element={
              <Suspense fallback={<PageSkeleton />}>
                <LoginPage />
              </Suspense>
            }
          />
          <Route element={<AppLayout />}>
            {APP_ROUTES.map((r) => {
              const Page = r.component;
              return <Route key={r.path} path={r.path} element={<Page />} />;
            })}
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </AppProviders>
    </BrowserRouter>
  </React.StrictMode>
);
