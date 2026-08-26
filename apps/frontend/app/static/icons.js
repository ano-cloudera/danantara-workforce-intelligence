import React from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import {
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  BadgeDollarSign,
  Bell,
  BookOpenCheck,
  Briefcase,
  BriefcaseBusiness,
  ChartPie,
  ChevronDown,
  CircleAlert,
  CloudUpload,
  Contact,
  Copy,
  Database,
  Download,
  ExternalLink,
  EyeOff,
  FileUser,
  Files,
  FlaskConical,
  Gauge,
  House,
  Info,
  Layers3,
  LockKeyhole,
  Menu,
  MessageSquarePlus,
  RotateCcw,
  ScanSearch,
  Search,
  Send,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  ThumbsDown,
  ThumbsUp,
  Upload,
  UserPlus,
  Users,
  Workflow,
  X,
} from "https://esm.sh/lucide-react@0.468.0?deps=react@18.3.1";

const icons = {
  "arrow-right": ArrowRight,
  "arrow-up-right": ArrowUpRight,
  "badge-check": BadgeCheck,
  "badge-dollar-sign": BadgeDollarSign,
  bell: Bell,
  "book-open-check": BookOpenCheck,
  briefcase: Briefcase,
  "briefcase-business": BriefcaseBusiness,
  "chart-pie": ChartPie,
  "chevron-down": ChevronDown,
  "circle-alert": CircleAlert,
  "cloud-upload": CloudUpload,
  contact: Contact,
  copy: Copy,
  database: Database,
  download: Download,
  "external-link": ExternalLink,
  "eye-off": EyeOff,
  "file-user": FileUser,
  files: Files,
  "flask-conical": FlaskConical,
  gauge: Gauge,
  house: House,
  info: Info,
  "layers-3": Layers3,
  "lock-keyhole": LockKeyhole,
  menu: Menu,
  "message-square-plus": MessageSquarePlus,
  "rotate-ccw": RotateCcw,
  "scan-search": ScanSearch,
  search: Search,
  send: Send,
  settings: Settings,
  "shield-check": ShieldCheck,
  "sliders-horizontal": SlidersHorizontal,
  target: Target,
  "thumbs-down": ThumbsDown,
  "thumbs-up": ThumbsUp,
  upload: Upload,
  "user-plus": UserPlus,
  users: Users,
  workflow: Workflow,
  x: X,
};

const roots = new WeakMap();

function renderLucideIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach(node => {
    const Icon = icons[node.dataset.icon];
    if (!Icon || node.dataset.iconRendered === "true") return;
    const context = node.dataset.context || "button";
    const props = context === "nav"
      ? { size: 20, strokeWidth: 1.75 }
      : context === "stat"
        ? { size: 24, strokeWidth: 1.5 }
        : { size: 16, strokeWidth: 2 };
    const iconRoot = createRoot(node);
    roots.set(node, iconRoot);
    iconRoot.render(React.createElement(Icon, {
      ...props,
      className: node.dataset.iconClass || "text-slate-500 hover:text-red-600 transition-colors",
      "aria-hidden": true,
    }));
    node.dataset.iconRendered = "true";
  });
}

window.renderLucideIcons = renderLucideIcons;
renderLucideIcons();
new MutationObserver(() => renderLucideIcons()).observe(document.body, { childList: true, subtree: true });
