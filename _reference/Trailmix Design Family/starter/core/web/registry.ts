// The web half of the module contract. Every modules/<id>/web/index.tsx default-exports a ModuleWeb;
// the host shows the ones the server says are enabled (app.json), in that order.
import type { ComponentType, ReactNode } from "react";

export interface RouteProps {
  params: Record<string, string>;
}

export interface NavItem {
  label: string;
  icon: ReactNode;
  /** Where it goes, without "#/": "notes". Highlighted for this path and anything under it. */
  path: string;
  /** A small count next to the label (it fetches its own number). */
  badge?: ComponentType;
}

export interface ModuleWeb {
  id: string; // must match the server module's id (and its folder)
  name: string;
  nav?: NavItem[];
  /** Paths are "<id>" or start with "<id>/", e.g. "notes/:id". */
  routes: { path: string; view: ComponentType<RouteProps> }[];
  /** The sidebar's big button. The first enabled module that has one gets it. */
  primary?: { label: string; icon: ReactNode; run: () => void | Promise<void> };
  /** A card on Home, where every module shows what's new. */
  home?: ComponentType;
  /** A section on the Settings page. */
  settings?: ComponentType;
}

const found = import.meta.glob<{ default: ModuleWeb }>("../../modules/*/web/index.tsx", { eager: true });
const byId = new Map(Object.values(found).map((m) => [m.default.id, m.default]));

export function modulesFor(ids: string[]): ModuleWeb[] {
  return ids.flatMap((id) => {
    const m = byId.get(id);
    if (!m) console.warn(`Module "${id}" is enabled on the server but has no web/index.tsx`);
    return m ? [m] : [];
  });
}
