/**
 * Single source of truth for pages: router, sidebar, breadcrumbs and the Ctrl/Cmd+K palette
 * are all generated from APP_ROUTES.
 *
 * To add a page (e.g. "/live", "/zero-day"):
 *   1. Create src/pages/LivePage.tsx exporting `LivePage`.
 *   2. Append an entry below:
 *        { path: "/live", label: "Live Capture", icon: Radio, section: "Operations",
 *          component: lazyPage(() => import("../pages/LivePage"), "LivePage"),
 *          description: "Real-time flow scoring", keywords: ["stream"] },
 *   That's it — the route, nav item, breadcrumb and palette entry appear automatically.
 *   Use `hideInNav: true` for detail routes with params (e.g. "/things/:id").
 */
import { lazy, type ComponentType, type LazyExoticComponent } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BookOpenCheck,
  BrainCircuit,
  FileBarChart2,
  FileWarning,
  FlaskConical,
  LayoutDashboard,
  Network,
  Radar,
  Radio,
  ServerCog,
  ShieldQuestion,
  Swords,
} from "lucide-react";

export type NavSection = "Operations" | "Zero-Day Research" | "Investigate" | "Lab";

/** Display order of sidebar groups. Add a new section name here to create a new group. */
export const NAV_SECTIONS: NavSection[] = ["Operations", "Zero-Day Research", "Investigate", "Lab"];

export interface AppRoute {
  /** react-router path (may contain params when hideInNav is true). */
  path: string;
  label: string;
  icon: LucideIcon;
  section: NavSection;
  component: LazyExoticComponent<ComponentType>;
  /** Match the nav link exactly (only for "/"). */
  end?: boolean;
  /** Keep out of the sidebar/palette (detail pages). */
  hideInNav?: boolean;
  /** Shown in the command palette. */
  description?: string;
  /** Extra search terms for the command palette. */
  keywords?: string[];
  /** Nav path to highlight / use as breadcrumb parent for hidden detail routes. */
  parent?: string;
}

/** Lazy-load a page module that uses a named export. */
export function lazyPage<M extends Record<string, unknown>>(loader: () => Promise<M>, exportName: keyof M & string) {
  return lazy(async () => {
    const mod = await loader();
    return { default: mod[exportName] as ComponentType };
  });
}

export const APP_ROUTES: AppRoute[] = [
  {
    path: "/",
    end: true,
    label: "Dashboard",
    icon: LayoutDashboard,
    section: "Operations",
    component: lazyPage(() => import("../pages/DashboardPage"), "DashboardPage"),
    description: "Live security overview and incident feed",
    keywords: ["home", "overview", "soc"],
  },
  {
    path: "/detection",
    label: "Detection",
    icon: Radar,
    section: "Operations",
    component: lazyPage(() => import("../pages/DetectionPage"), "DetectionPage"),
    description: "Classify flows, explain predictions, upload CSV / PCAP",
    keywords: ["predict", "shap", "lime", "upload", "pcap", "csv"],
  },
  {
    path: "/range",
    label: "Cyber Range",
    icon: Swords,
    section: "Operations",
    component: lazyPage(() => import("../pages/CyberRangePage"), "CyberRangePage"),
    description: "Run an attack in a virtual network: real detectors, your response, measured outcome",
    keywords: ["cyber range", "simulation", "scenario", "defense", "experiment", "mitigation", "attack"],
  },
  {
    path: "/simulation",
    label: "Attack Storyboard",
    icon: Network,
    section: "Operations",
    component: lazyPage(() => import("../pages/SimulationPage"), "SimulationPage"),
    description: "Illustrative attack → detect → defend → recover walkthrough (assumed values, not measured)",
    keywords: ["topology", "storyboard", "walkthrough", "defense", "simulation"],
  },
  {
    path: "/live",
    label: "Live Monitor",
    icon: Radio,
    section: "Zero-Day Research",
    component: lazyPage(() => import("../pages/LiveMonitorPage"), "LiveMonitorPage"),
    description: "Replayed traffic scored by the frozen model and the Zero-Day Gate in real time",
    keywords: ["live", "stream", "traffic", "replay", "zero-day", "websocket"],
  },
  {
    path: "/zero-day",
    label: "Zero-Day Lab",
    icon: ShieldQuestion,
    section: "Zero-Day Research",
    component: lazyPage(() => import("../pages/ZeroDayLabPage"), "ZeroDayLabPage"),
    description: "How the open-set gate decides — try a flow, tune α",
    keywords: ["aegis-osr", "open-set", "conformal", "novelty", "alpha", "unknown"],
  },
  {
    path: "/research-lab",
    label: "Research Lab",
    icon: FlaskConical,
    section: "Zero-Day Research",
    component: lazyPage(() => import("../pages/ResearchLabPage"), "ResearchLabPage"),
    description: "LOAFO, temporal and cross-dataset open-set results",
    keywords: ["loafo", "temporal", "cross-dataset", "significance", "experiments", "ci"],
  },
  {
    path: "/reports",
    label: "Reports",
    icon: FileBarChart2,
    section: "Investigate",
    component: lazyPage(() => import("../pages/ReportsPage"), "ReportsPage"),
    description: "Incident registry, triage and exports",
    keywords: ["incidents", "export", "pdf", "csv"],
  },
  {
    path: "/campaigns",
    label: "Campaigns",
    icon: Activity,
    section: "Investigate",
    component: lazyPage(() => import("../pages/CampaignPage"), "CampaignPage"),
    description: "Correlated multi-incident investigations",
    keywords: ["correlation"],
  },
  {
    path: "/campaigns/:campaignId",
    label: "Campaign",
    icon: Activity,
    section: "Investigate",
    hideInNav: true,
    parent: "/campaigns",
    component: lazyPage(() => import("../pages/CampaignPage"), "CampaignPage"),
  },
  {
    path: "/incidents/:incidentId",
    label: "Incident",
    icon: FileWarning,
    section: "Investigate",
    hideInNav: true,
    parent: "/reports",
    component: lazyPage(() => import("../pages/IncidentDetailPage"), "IncidentDetailPage"),
  },
  {
    path: "/models",
    label: "Models",
    icon: BrainCircuit,
    section: "Lab",
    component: lazyPage(() => import("../pages/ModelsPage"), "ModelsPage"),
    description: "Performance, explainability and drift",
    keywords: ["confusion matrix", "shap", "drift", "psi", "metrics"],
  },
  {
    path: "/research",
    label: "Baseline study (v1.1)",
    icon: BookOpenCheck,
    section: "Lab",
    component: lazyPage(() => import("../pages/ResearchPage"), "ResearchPage"),
    description: "Frozen v1.1 experiment conclusions",
    keywords: ["experiments", "viva", "results"],
  },
  {
    path: "/system",
    label: "System",
    icon: ServerCog,
    section: "Lab",
    component: lazyPage(() => import("../pages/SystemPage"), "SystemPage"),
    description: "Operational health, dependencies and alerts",
    keywords: ["ops", "health", "latency", "status"],
  },
];

export const NAV_ROUTES = APP_ROUTES.filter((r) => !r.hideInNav);

/** Find the route config for a pathname (for breadcrumbs / titles). */
export function matchRoute(pathname: string): AppRoute | undefined {
  const exact = APP_ROUTES.find((r) => r.path === pathname);
  if (exact) return exact;
  return APP_ROUTES.find((r) => {
    if (!r.path.includes(":")) return false;
    const re = new RegExp(`^${r.path.replace(/:[^/]+/g, "[^/]+")}$`);
    return re.test(pathname);
  });
}
