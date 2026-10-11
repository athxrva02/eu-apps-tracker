import { StrictMode, useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Bookmark,
  BriefcaseBusiness,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  ExternalLink,
  FileText,
  FlaskConical,
  Globe2,
  Leaf,
  LoaderCircle,
  Mail,
  MapPin,
  Plus,
  Radio,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Sprout,
  Upload,
  UserRound,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type {
  Activity,
  AppSettings,
  Job,
  Overview,
  Profile,
  Source,
} from "./types";
import {
  api,
  countries,
  dateTime,
  errorMessage,
  publicationLabel,
} from "./utils";
import "./style.css";

type Page = "Jobs" | "Profile" | "Sources" | "Activity" | "Settings";
const navigation: [Page, LucideIcon][] = [
  ["Jobs", BriefcaseBusiness],
  ["Profile", UserRound],
  ["Sources", Radio],
  ["Activity", RefreshCw],
  ["Settings", Settings2],
];
const statusOptions = [
  "new",
  "saved",
  "dismissed",
  "applied",
  "interview",
  "offer",
  "archived",
];
const dimensionNames: Record<string, string> = {
  scope: "Executive scope",
  function: "Function fit",
  sector: "Sector fit",
  capability: "Experience & capability",
  geography: "Geography",
};

function Badge({
  children,
  tone = "",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
function Empty({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="empty">
      <Sprout size={32} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panel.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close.current();
      if (event.key === "Tab" && panel.current) {
        const nodes = Array.from(
          panel.current.querySelectorAll<HTMLElement>(
            'button, a, input, select, textarea, [tabindex="0"]',
          ),
        ).filter((e) => !e.hasAttribute("disabled"));
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = before;
      window.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, []);
  return (
    <div
      className="overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={`modal ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={panel}
      >
        <div className="modal-heading">
          <h2>{title}</h2>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function App() {
  const [page, setPage] = useState<Page>("Jobs");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [activity, setActivity] = useState<Activity | null>(null);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [auth, setAuth] = useState("");
  const [detail, setDetail] = useState<Job | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState<Source | "new" | null>(null);
  const [tab, setTab] = useState("All opportunities");
  const [query, setQuery] = useState("");
  const [country, setCountry] = useState("");
  const [freshness, setFreshness] = useState("all");
  const [hours, setHours] = useState("24");
  const [extraFilters, setExtraFilters] = useState(false);
  const [company, setCompany] = useState("");
  const [workMode, setWorkMode] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [functionFilter, setFunctionFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [scoreFilter, setScoreFilter] = useState("0");
  const [visibleLimit, setVisibleLimit] = useState(30);
  useEffect(
    () => setVisibleLimit(30),
    [
      tab,
      query,
      country,
      freshness,
      hours,
      company,
      workMode,
      sourceFilter,
      functionFilter,
      statusFilter,
      scoreFilter,
    ],
  );
  const refresh = useCallback(async () => {
    const results = await Promise.all([
      api<Overview>("/overview"),
      api<Job[]>("/jobs"),
      api<Source[]>("/sources"),
      api<Profile[]>("/profiles"),
      api<AppSettings>("/settings"),
      api<Activity>("/activity"),
    ]);
    setOverview(results[0]);
    setJobs(results[1]);
    setSources(results[2]);
    setProfiles(results[3]);
    setSettings(results[4]);
    setActivity(results[5]);
    setError("");
  }, []);
  useEffect(() => {
    refresh()
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setLoading(false));
  }, [refresh]);
  useEffect(() => {
    const id = window.setInterval(() => refresh().catch(() => {}), 15000);
    return () => clearInterval(id);
  }, [refresh]);
  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(""), 6000);
    return () => clearTimeout(id);
  }, [toast]);
  const act = async (action: () => Promise<unknown>, message: string) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await refresh();
      setToast(message);
      return true;
    } catch (e) {
      setError(errorMessage(e));
      return false;
    } finally {
      setBusy(false);
    }
  };
  const saveJob = async (job: Job, status: string) => {
    const saved = await act(
      () =>
        api(`/jobs/${job.id}`, {
          method: "PATCH",
          body: JSON.stringify({ status }),
        }),
      status === "saved"
        ? "Opportunity saved to your shortlist."
        : `Status updated to ${status}.`,
    );
    if (saved && detail?.id === job.id)
      setDetail({ ...detail, candidate_status: status });
  };
  const timezone = overview?.timezone || "Europe/Berlin";
  const high = settings?.high_threshold || 80;
  const review = settings?.review_threshold || 65;
  const visible = jobs.filter((job) => {
    const match = job.match;
    if (
      tab === "High matches" &&
      (!match ||
        match.score < high ||
        match.provisional ||
        match.hard_filters.length)
    )
      return false;
    if (tab === "Saved" && job.candidate_status !== "saved") return false;
    if (
      tab === "Needs review" &&
      (!match ||
        match.score < review ||
        (match.score >= high && !match.provisional))
    )
      return false;
    if (
      !`${job.title} ${job.company}`.toLowerCase().includes(query.toLowerCase())
    )
      return false;
    if (country && !job.data.countries.includes(country)) return false;
    if (
      (company && job.company !== company) ||
      (workMode && job.data.work_mode !== workMode) ||
      (statusFilter && job.candidate_status !== statusFilter)
    )
      return false;
    if (sourceFilter && !job.sources.some((s) => s.id === Number(sourceFilter)))
      return false;
    if (
      functionFilter &&
      !`${job.title} ${job.data.description}`
        .toLowerCase()
        .includes(functionFilter.toLowerCase())
    )
      return false;
    if (Number(scoreFilter) && (match?.score || 0) < Number(scoreFilter))
      return false;
    const cutoff = Date.now() - Number(hours) * 3600000;
    if (
      freshness === "discovered" &&
      new Date(job.first_seen_at).getTime() < cutoff
    )
      return false;
    if (freshness === "published") {
      const p = job.data.publication;
      if (
        !p?.start ||
        !p.end ||
        new Date(p.start).getTime() < cutoff ||
        new Date(p.end).getTime() > Date.now()
      )
        return false;
    }
    return true;
  });
  const activeProfile = profiles.find((p) => p.approved);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("Jobs");
          }}
        >
          <span className="brand-icon">
            <Sprout size={25} />
          </span>
          fieldwork<span className="brand-period">.</span>
        </a>
        <div className="workspace-label">YOUR NEXT CHAPTER</div>
        <nav aria-label="Main navigation">
          {navigation.map(([name, Icon]) => (
            <button
              key={name}
              onClick={() => setPage(name)}
              className={`nav-item ${page === name ? "active" : ""}`}
              aria-current={page === name ? "page" : undefined}
            >
              <Icon size={19} />
              <span>{name === "Jobs" ? "Opportunities" : name}</span>
              {name === "Jobs" && (
                <span className="nav-count">{overview?.total_jobs ?? "—"}</span>
              )}
              {name === "Sources" && !!overview?.stale_sources && (
                <span className="nav-dot" />
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="private-note">
            <ShieldCheck size={18} />
            <div>
              <strong>Your search, privately.</strong>
              <p>One profile. A considered next move.</p>
            </div>
          </div>
          <button className="profile-switch" onClick={() => setPage("Profile")}>
            <div className="avatar">
              {activeProfile?.data.demo ? "D" : "MD"}
            </div>
            <div>
              <strong>
                {activeProfile?.data.demo ? "Demo workspace" : "My workspace"}
              </strong>
              <span>
                {activeProfile ? "Profile approved" : "Complete your profile"}
              </span>
            </div>
            <ChevronDown size={15} />
          </button>
        </div>
      </aside>
      <div className="main-wrap">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />{" "}
            <span>{page === "Jobs" ? "Opportunities" : page}</span>
          </div>
          <div className="topbar-right">
            <span className="timezone">
              <Globe2 size={14} />
              {timezone}
            </span>
            <span className="privacy-pill">
              <span /> Local workspace
            </span>
            <button
              className="icon-button"
              onClick={() => setPage("Activity")}
              aria-label="Notification activity"
            >
              <Bell size={18} />
            </button>
          </div>
        </header>
        {overview?.demo && (
          <div className="demo-banner">
            <FlaskConical size={16} />
            <span>
              <strong>Demo workspace</strong> · Every vacancy and candidate
              detail shown here is synthetic.
            </span>
            <button
              onClick={() =>
                act(
                  () => api("/demo/advance", { method: "POST" }),
                  "Demo scan completed. Open Activity for the notification preview.",
                )
              }
              disabled={busy}
            >
              <Sparkles size={14} /> Discover a new demo job{" "}
              <ArrowRight size={14} />
            </button>
          </div>
        )}
        <main>
          {error && (
            <div className="error-banner" role="alert">
              <CircleHelp size={19} />
              <span>{error}</span>
              <button
                className="icon-button"
                onClick={() => setError("")}
                aria-label="Dismiss error"
              >
                <X size={16} />
              </button>
            </div>
          )}
          {!overview && !loading && (
            <section className="card auth-card">
              <h2>Connect to your workspace</h2>
              <p>
                If authentication is enabled, enter your admin token. Otherwise
                verify the API is running and migrations have been applied.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  sessionStorage.setItem("agent-token", auth);
                  act(refresh, "Workspace connected.");
                }}
              >
                <label>
                  Admin token
                  <input
                    type="password"
                    value={auth}
                    onChange={(e) => setAuth(e.target.value)}
                    autoComplete="off"
                  />
                </label>
                <button className="primary">Connect</button>
              </form>
            </section>
          )}
          {loading ? (
            <div className="loading">
              <LoaderCircle className="spin" /> Preparing your workspace…
            </div>
          ) : (
            overview && (
              <>
                {page === "Jobs" && (
                  <>
                    <div className="page-heading">
                      <div>
                        <div className="eyebrow">
                          <span className="small-line" /> A MORE INTENTIONAL
                          SEARCH
                        </div>
                        <h1>Find your next chapter.</h1>
                        <p>
                          Relevant leadership opportunities, with the evidence
                          to decide.
                        </p>
                      </div>
                      <button
                        className="secondary"
                        onClick={() => setImportOpen(true)}
                      >
                        <Upload size={16} /> Import opportunities
                      </button>
                    </div>
                    <div className="metrics">
                      {[
                        [
                          BriefcaseBusiness,
                          "Opportunities discovered",
                          overview.total_jobs,
                          "Across your configured sources",
                        ],
                        [
                          Sparkles,
                          "High matches",
                          overview.high_matches,
                          `Score ${high}+ with sufficient evidence`,
                        ],
                        [
                          Bookmark,
                          "Your shortlist",
                          overview.saved,
                          "Saved for a closer look",
                        ],
                        [
                          Radio,
                          "Sources enabled",
                          overview.enabled_sources,
                          `${sources.filter((s) => s.kind === "unsupported").length} targets need onboarding`,
                        ],
                      ].map(([Icon, label, value, note], index) => {
                        const MetricIcon = Icon as LucideIcon;
                        return (
                          <div
                            className={`metric metric-${index}`}
                            key={String(label)}
                          >
                            <div className="metric-label">
                              <span>{String(label)}</span>
                              <MetricIcon size={17} />
                            </div>
                            <div className="metric-value">
                              {String(value)}
                              {index === 3 && <span className="live-dot" />}
                            </div>
                            <div className="metric-note">{String(note)}</div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="jobs-layout">
                      <section className="job-section">
                        <div className="section-title">
                          <h2>
                            Your opportunities <span>{visible.length}</span>
                          </h2>
                          <span className="sort-label">
                            Best match first <ChevronDown size={14} />
                          </span>
                        </div>
                        <div
                          className="tabs"
                          role="tablist"
                          aria-label="Opportunity lists"
                        >
                          {[
                            "All opportunities",
                            "High matches",
                            "Saved",
                            "Needs review",
                          ].map((name) => (
                            <button
                              role="tab"
                              aria-selected={tab === name}
                              className={tab === name ? "selected" : ""}
                              onClick={() => setTab(name)}
                              key={name}
                            >
                              {name}
                            </button>
                          ))}
                        </div>
                        <div className="filters">
                          <label className="search-field">
                            <Search size={17} />
                            <input
                              aria-label="Search opportunities"
                              placeholder="Search roles or companies"
                              value={query}
                              onChange={(e) => setQuery(e.target.value)}
                            />
                          </label>
                          <select
                            aria-label="Country"
                            value={country}
                            onChange={(e) => setCountry(e.target.value)}
                          >
                            <option value="">All countries</option>
                            {Object.entries(countries).map(([code, name]) => (
                              <option value={code} key={code}>
                                {name}
                              </option>
                            ))}
                          </select>
                          <button
                            className={`filter-button ${extraFilters ? "on" : ""}`}
                            onClick={() => setExtraFilters(!extraFilters)}
                          >
                            <SlidersHorizontal size={16} />
                            Filters
                          </button>
                        </div>
                        {extraFilters && (
                          <div className="advanced-filters">
                            <label>
                              Freshness basis
                              <select
                                value={freshness}
                                onChange={(e) => setFreshness(e.target.value)}
                              >
                                <option value="all">Any time</option>
                                <option value="discovered">
                                  Discovered recently
                                </option>
                                <option value="published">
                                  Published recently
                                </option>
                              </select>
                            </label>
                            <label>
                              Time window
                              <select
                                value={hours}
                                onChange={(e) => setHours(e.target.value)}
                              >
                                <option value="1">Last hour</option>
                                <option value="24">Last 24 hours</option>
                                <option value="168">Last 7 days</option>
                              </select>
                            </label>
                            <label>
                              Company
                              <select
                                value={company}
                                onChange={(e) => setCompany(e.target.value)}
                              >
                                <option value="">All companies</option>
                                {[...new Set(jobs.map((j) => j.company))].map(
                                  (c) => (
                                    <option key={c}>{c}</option>
                                  ),
                                )}
                              </select>
                            </label>
                            <label>
                              Work mode
                              <select
                                value={workMode}
                                onChange={(e) => setWorkMode(e.target.value)}
                              >
                                <option value="">All work modes</option>
                                {["hybrid", "remote", "on-site", "unknown"].map(
                                  (v) => (
                                    <option key={v}>{v}</option>
                                  ),
                                )}
                              </select>
                            </label>
                            <label>
                              Source
                              <select
                                value={sourceFilter}
                                onChange={(e) =>
                                  setSourceFilter(e.target.value)
                                }
                              >
                                <option value="">All sources</option>
                                {sources
                                  .filter((s) => s.kind !== "unsupported")
                                  .map((s) => (
                                    <option key={s.id} value={s.id}>
                                      {s.name}
                                    </option>
                                  ))}
                              </select>
                            </label>
                            <label>
                              Function keyword
                              <input
                                value={functionFilter}
                                onChange={(e) =>
                                  setFunctionFilter(e.target.value)
                                }
                                placeholder="e.g. formulation"
                              />
                            </label>
                            <label>
                              Candidate status
                              <select
                                value={statusFilter}
                                onChange={(e) =>
                                  setStatusFilter(e.target.value)
                                }
                              >
                                <option value="">All statuses</option>
                                {statusOptions.map((s) => (
                                  <option key={s}>{s}</option>
                                ))}
                              </select>
                            </label>
                            <label>
                              Minimum score
                              <input
                                type="number"
                                min="0"
                                max="100"
                                value={scoreFilter}
                                onChange={(e) => setScoreFilter(e.target.value)}
                              />
                            </label>
                          </div>
                        )}
                        <div className="job-list">
                          {visible.length ? (
                            visible.slice(0, visibleLimit).map((job) => (
                              <article className="job-card" key={job.id}>
                                <div
                                  className={`company-mark mark-${job.id % 4}`}
                                >
                                  {job.company
                                    .split(" ")
                                    .slice(0, 2)
                                    .map((s) => s[0])
                                    .join("")}
                                </div>
                                <div className="job-content">
                                  <div className="job-company">
                                    {job.company}
                                    {job.data.demo && <span>SYNTHETIC</span>}
                                  </div>
                                  <button
                                    className="job-title"
                                    onClick={() => setDetail(job)}
                                  >
                                    {job.title}
                                  </button>
                                  <div className="job-meta">
                                    <span>
                                      <MapPin size={13} />
                                      {job.data.locations.join(" · ") ||
                                        "Location unknown"}
                                    </span>
                                    <span className="meta-dot">·</span>
                                    <span>
                                      {job.data.work_mode === "unknown"
                                        ? "Work mode unspecified"
                                        : job.data.work_mode}
                                    </span>
                                  </div>
                                  <div className="job-tags">
                                    {job.match?.hard_filters.length ? (
                                      <Badge tone="muted">
                                        Outside current criteria
                                      </Badge>
                                    ) : job.match?.provisional ? (
                                      <Badge tone="amber">
                                        Limited evidence
                                      </Badge>
                                    ) : job.match && job.match.score >= high ? (
                                      <Badge tone="green">
                                        <Sparkles size={11} />
                                        High match
                                      </Badge>
                                    ) : job.match &&
                                      job.match.score >= review ? (
                                      <Badge tone="amber">
                                        Worth reviewing
                                      </Badge>
                                    ) : (
                                      <Badge tone="muted">Lower match</Badge>
                                    )}
                                    <span className="publication-note">
                                      {publicationLabel(
                                        job.data.publication,
                                        timezone,
                                      )}
                                    </span>
                                  </div>
                                  <div className="job-bottom">
                                    <span>
                                      Discovered{" "}
                                      {dateTime(job.first_seen_at, timezone)} ·{" "}
                                      {job.sources[0]?.name || "Imported"}
                                    </span>
                                    {job.availability !== "open" && (
                                      <Badge tone="muted">
                                        {job.availability === "unverified"
                                          ? "Availability unverified"
                                          : "Closed"}
                                      </Badge>
                                    )}
                                  </div>
                                </div>
                                <div className="job-actions">
                                  <div
                                    className={`score ${job.match && job.match.score >= high ? "strong" : ""}`}
                                  >
                                    <span>{job.match?.score ?? "—"}</span>
                                    <small>FIT SCORE</small>
                                  </div>
                                  <button
                                    className={`save-button ${job.candidate_status === "saved" ? "is-saved" : ""}`}
                                    aria-label={`${job.candidate_status === "saved" ? "Unsave" : "Save"} ${job.title}`}
                                    onClick={() =>
                                      saveJob(
                                        job,
                                        job.candidate_status === "saved"
                                          ? "new"
                                          : "saved",
                                      )
                                    }
                                    disabled={busy}
                                  >
                                    <Bookmark
                                      size={18}
                                      fill={
                                        job.candidate_status === "saved"
                                          ? "currentColor"
                                          : "none"
                                      }
                                    />
                                  </button>
                                  <button
                                    className="details-link"
                                    onClick={() => setDetail(job)}
                                  >
                                    View fit <ArrowUpRight size={14} />
                                  </button>
                                </div>
                              </article>
                            ))
                          ) : (
                            <Empty
                              title={
                                jobs.length
                                  ? "No opportunities in this view"
                                  : overview.profile_approved
                                    ? "Your search starts here"
                                    : "Approve your profile to start matching"
                              }
                            >
                              {jobs.length
                                ? "Try adjusting your filters or choose another list."
                                : overview.profile_approved
                                  ? "Connect a supported source or import vacancies. Source failures are shown in Activity."
                                  : "Review and approve candidate evidence in Profile."}
                            </Empty>
                          )}
                        </div>
                        <div className="list-footer">
                          {visible.length > visibleLimit && (
                            <button
                              className="secondary"
                              onClick={() =>
                                setVisibleLimit((limit) => limit + 30)
                              }
                            >
                              Show more ({visible.length - visibleLimit}{" "}
                              remaining)
                            </button>
                          )}
                          <ShieldCheck size={14} /> Fit scores are heuristic
                          rankings. Always review the original posting.
                        </div>
                      </section>
                      <aside className="insights">
                        <div className="search-card">
                          <div className="card-overline">
                            <Globe2 size={15} /> YOUR SEARCH
                          </div>
                          <h3>Ambition, with direction.</h3>
                          <p>A focused search for your next leadership role.</p>
                          <div className="map-pattern" aria-hidden="true">
                            <div className="map-orbit orbit-one" />
                            <div className="map-orbit orbit-two" />
                            <span className="map-point p1" />
                            <span className="map-point p2" />
                            <span className="map-point p3" />
                            <span className="map-point p4" />
                            <Globe2 size={94} strokeWidth={0.6} />
                          </div>
                          <div className="search-detail">
                            <span>Role families</span>
                            <strong>
                              R&D · Innovation
                              <br />
                              Product & technology
                            </strong>
                          </div>
                          <div className="search-detail">
                            <span>Preferred regions</span>
                            <div className="country-pills">
                              {settings?.countries.map((c) => (
                                <span key={c}>{c}</span>
                              ))}
                            </div>
                          </div>
                          <button
                            className="text-button"
                            onClick={() => setPage("Settings")}
                          >
                            Refine your preferences <ArrowRight size={14} />
                          </button>
                        </div>
                        <div className="card profile-health">
                          <div className="round-icon">
                            <FileText size={18} />
                          </div>
                          <h3>
                            {overview.profile_approved
                              ? "Built on your experience"
                              : "Your experience comes first"}
                          </h3>
                          <p>
                            {overview.profile_approved
                              ? "Every match is compared with approved profile evidence. Unknowns stay visible."
                              : "Upload, review and approve your résumé before matching."}
                          </p>
                          <button
                            className="text-button"
                            onClick={() => setPage("Profile")}
                          >
                            Review your profile <ArrowRight size={14} />
                          </button>
                        </div>
                        <div className="coverage-note">
                          <Radio size={16} />
                          <div>
                            <strong>Know what’s covered.</strong>
                            <p>
                              Company checklists are search targets. Only
                              validated sources are monitored.
                            </p>
                            <button onClick={() => setPage("Sources")}>
                              View source coverage <ArrowUpRight size={12} />
                            </button>
                          </div>
                        </div>
                      </aside>
                    </div>
                  </>
                )}
                {page === "Profile" && (
                  <ProfilePage profiles={profiles} busy={busy} act={act} />
                )}
                {page === "Sources" && (
                  <>
                    <PageHeading
                      eyebrow="DISCOVERY, WITH TRANSPARENCY"
                      title="A clear view of your sources."
                      description="Supported integrations, target employers, and the gaps between them."
                      action={
                        <button
                          className="primary"
                          onClick={() => setSourceOpen("new")}
                        >
                          <Plus size={16} />
                          Add source
                        </button>
                      }
                    />
                    <div className="info-callout">
                      <CircleHelp size={18} />
                      <span>
                        LinkedIn is available through uploaded job-alert emails.
                        No automated browsing or one-hour coverage is promised.
                      </span>
                      <button onClick={() => setImportOpen(true)}>
                        Import an alert <ArrowRight size={14} />
                      </button>
                    </div>
                    <div className="source-grid">
                      {sources
                        .filter((s) => !s.capability.archived)
                        .map((source) => (
                          <div className="card source-card" key={source.id}>
                            <div className="source-top">
                              <div
                                className={`company-mark mark-${source.id % 4}`}
                              >
                                {source.company.slice(0, 2).toUpperCase()}
                              </div>
                              <Badge
                                tone={
                                  source.kind === "unsupported"
                                    ? "muted"
                                    : source.last_error
                                      ? "amber"
                                      : source.enabled
                                        ? "green"
                                        : ""
                                }
                              >
                                {source.kind === "unsupported"
                                  ? "Unsupported"
                                  : source.last_error
                                    ? "Needs attention"
                                    : source.enabled
                                      ? "Enabled"
                                      : "Paused"}
                              </Badge>
                            </div>
                            <h3>{source.name}</h3>
                            <div className="source-kind">
                              {source.kind === "demo"
                                ? "Synthetic demo connector"
                                : source.kind === "unsupported"
                                  ? "Target employer · onboarding required"
                                  : `${source.kind} connector`}
                            </div>
                            {source.url && (
                              <a
                                className="source-url"
                                href={source.url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Official careers <ExternalLink size={12} />
                              </a>
                            )}
                            <p className="source-note">
                              {source.last_error ||
                                source.capability.error ||
                                source.capability.note ||
                                (source.kind === "demo"
                                  ? "Recorded synthetic vacancies; no external requests."
                                  : `Every ${source.interval_minutes} minutes · last success ${dateTime(source.last_success, timezone)}`)}
                            </p>
                            <div className="source-footer">
                              {source.kind === "unsupported" ? (
                                <button
                                  className="text-button"
                                  onClick={() => setSourceOpen(source)}
                                >
                                  Configure integration <ArrowRight size={14} />
                                </button>
                              ) : (
                                <>
                                  <button
                                    className="small-button"
                                    disabled={busy}
                                    onClick={() =>
                                      act(
                                        () =>
                                          api(`/sources/${source.id}/test`, {
                                            method: "POST",
                                          }),
                                        "Connection test finished. Check source capabilities.",
                                      )
                                    }
                                  >
                                    Test
                                  </button>
                                  <button
                                    className="small-button"
                                    disabled={busy}
                                    onClick={() =>
                                      act(
                                        () =>
                                          api(`/sources/${source.id}/scan`, {
                                            method: "POST",
                                          }),
                                        "Scan completed; review Activity for completeness.",
                                      )
                                    }
                                  >
                                    Scan
                                  </button>
                                  <button
                                    className="icon-button"
                                    aria-label={`Configure ${source.name}`}
                                    onClick={() => setSourceOpen(source)}
                                  >
                                    <Settings2 size={15} />
                                  </button>
                                  <button
                                    className="small-button"
                                    disabled={busy}
                                    onClick={() =>
                                      act(
                                        () =>
                                          api(`/sources/${source.id}`, {
                                            method: "PATCH",
                                            body: JSON.stringify({
                                              enabled: !source.enabled,
                                            }),
                                          }),
                                        source.enabled
                                          ? "Source paused."
                                          : "Source enabled.",
                                      )
                                    }
                                  >
                                    {source.enabled ? "Pause" : "Enable"}
                                  </button>
                                </>
                              )}
                            </div>
                          </div>
                        ))}
                    </div>
                  </>
                )}
                {page === "Activity" && activity && (
                  <>
                    <PageHeading
                      eyebrow="EVERY STEP, ACCOUNTED FOR"
                      title="The work behind your search."
                      description="Scan health, notification delivery, and model usage in one place."
                      action={
                        <button
                          className="secondary"
                          onClick={() => act(refresh, "Activity refreshed.")}
                        >
                          <RefreshCw size={15} />
                          Refresh
                        </button>
                      }
                    />
                    <div className="worker-status">
                      <span
                        className={
                          overview.worker &&
                          Date.now() -
                            new Date(overview.worker.last_tick).getTime() <
                            120000
                            ? "live-dot"
                            : "neutral-dot"
                        }
                      />
                      <strong>
                        {overview.worker &&
                        Date.now() -
                          new Date(overview.worker.last_tick).getTime() <
                          120000
                          ? "Worker active"
                          : "Worker heartbeat not detected"}
                      </strong>
                      <span>
                        Last tick:{" "}
                        {dateTime(overview.worker?.last_tick || null, timezone)}{" "}
                        · source schedules persist in the database
                      </span>
                    </div>
                    <section className="card activity-table">
                      <h2>Recent scans</h2>
                      {activity.runs.length ? (
                        <div className="table-scroll">
                          <table>
                            <thead>
                              <tr>
                                <th>Source</th>
                                <th>Started</th>
                                <th>Result</th>
                                <th>Vacancies</th>
                                <th>New</th>
                                <th>Completeness</th>
                              </tr>
                            </thead>
                            <tbody>
                              {activity.runs.map((run) => (
                                <tr key={run.id}>
                                  <td>
                                    <strong>
                                      {sources.find(
                                        (s) => s.id === run.source_id,
                                      )?.name || `Source ${run.source_id}`}
                                    </strong>
                                    {run.error && (
                                      <small className="table-error">
                                        {run.error}
                                      </small>
                                    )}
                                  </td>
                                  <td>{dateTime(run.started_at, timezone)}</td>
                                  <td>
                                    <Badge
                                      tone={
                                        run.status === "success"
                                          ? "green"
                                          : run.status === "running"
                                            ? ""
                                            : "amber"
                                      }
                                    >
                                      {run.status}
                                    </Badge>
                                  </td>
                                  <td>{run.count}</td>
                                  <td>{run.new_count}</td>
                                  <td>
                                    {run.complete ? "Complete" : "Incomplete"}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <Empty title="No scans yet">
                          Run a source connection test and baseline scan to
                          begin.
                        </Empty>
                      )}
                    </section>
                    <section className="card activity-table">
                      <h2>Notification ledger</h2>
                      <p className="section-description">
                        “Delivered” means SMTP accepted the message. Unknown
                        acknowledgement is never blindly resent.
                      </p>
                      {activity.notifications.length ? (
                        activity.notifications.map((n) => (
                          <details className="notification-item" key={n.id}>
                            <summary>
                              <Mail size={17} />
                              <strong>
                                {n.type === "discovery"
                                  ? "New opportunity alert"
                                  : n.type === "digest"
                                    ? "Daily digest"
                                    : "Connection test"}
                              </strong>
                              <span>{dateTime(n.created_at, timezone)}</span>
                              <Badge
                                tone={
                                  n.status === "preview" ||
                                  n.status === "delivered"
                                    ? "green"
                                    : "amber"
                                }
                              >
                                {n.status}
                              </Badge>
                              <ChevronDown size={14} />
                            </summary>
                            <pre>{n.body}</pre>
                            <p>
                              Attempts: {n.attempts} · due{" "}
                              {dateTime(n.due_at, timezone)}
                            </p>
                            {activity.delivery_attempts
                              .filter((a) => a.notification_id === n.id)
                              .map((a, i) => (
                                <p key={i}>
                                  {a.status}: {a.error || a.provider_id}
                                </p>
                              ))}
                          </details>
                        ))
                      ) : (
                        <Empty title="A quiet inbox, by design">
                          Baseline imports do not send immediate alerts. New
                          eligible matches appear here after later scans.
                        </Empty>
                      )}
                    </section>
                    <section className="card activity-table">
                      <h2>Model usage</h2>
                      <p>
                        ${overview.model_cost_usd.toFixed(5)} spent or reserved
                        of ${overview.budget_usd.toFixed(2)} this month.
                        Fetching and deterministic matching continue when the
                        budget is exhausted.
                      </p>
                      {activity.model_usage.map((u) => (
                        <div className="usage-row" key={u.id}>
                          <Badge>{u.status}</Badge>
                          <span>{u.tokens} tokens</span>
                          <span>
                            ${(u.actual_usd ?? u.reserved_usd).toFixed(5)}
                          </span>
                        </div>
                      ))}
                    </section>
                  </>
                )}
                {page === "Settings" && settings && (
                  <SettingsPage settings={settings} busy={busy} act={act} />
                )}
              </>
            )
          )}
        </main>
        <footer className="app-footer">
          <span>
            <Leaf size={12} /> A thoughtful search. An informed next step.
          </span>
          <span>Fieldwork · Private executive discovery</span>
        </footer>
      </div>
      {toast && (
        <div className="toast" role="status">
          <Check size={17} />
          {toast}
          <button
            onClick={() => setToast("")}
            aria-label="Dismiss notification"
          >
            <X size={15} />
          </button>
        </div>
      )}
      {busy && (
        <div className="working" role="status">
          <LoaderCircle size={15} className="spin" />
          Working…
        </div>
      )}
      {detail && (
        <Modal title="Opportunity details" wide onClose={() => setDetail(null)}>
          <div className="detail-company">
            {detail.company}
            {detail.data.demo && <Badge tone="amber">Synthetic vacancy</Badge>}
          </div>
          <h1 className="detail-title">{detail.title}</h1>
          <div className="detail-meta">
            <MapPin size={15} />
            {detail.data.locations.join(" · ") || "Location unknown"}
            <Badge>{detail.availability}</Badge>
          </div>
          <div className="detail-toolbar">
            <a
              className="primary"
              href={detail.url}
              target="_blank"
              rel="noreferrer"
            >
              Open original posting <ArrowUpRight size={15} />
            </a>
            <label>
              Candidate status
              <select
                value={detail.candidate_status}
                onChange={(e) => saveJob(detail, e.target.value)}
              >
                {statusOptions.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>
          </div>
          {detail.match ? (
            <>
              <div className="match-header">
                <div className="big-score">
                  {detail.match.score}
                  <span>/100</span>
                </div>
                <div>
                  <h3>{detail.match.recommendation}</h3>
                  <p>
                    {detail.match.method} ·{" "}
                    {detail.match.provisional
                      ? "Limited evidence"
                      : "Sufficient description evidence"}
                  </p>
                </div>
              </div>
              <div className="dimension-grid">
                {Object.entries(detail.match.dimensions).map(([key, value]) => (
                  <div key={key}>
                    <span>{dimensionNames[key]}</span>
                    <strong>
                      {value}/{settings?.weights[key]}
                    </strong>
                    <div className="progress">
                      <span
                        style={{
                          width: `${(100 * value) / (settings?.weights[key] || 1)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              {!!detail.match.hard_filters.length && (
                <div className="info-callout amber">
                  <CircleHelp size={18} />
                  {detail.match.hard_filters.join(" · ")}
                </div>
              )}
              <h3 className="detail-section-title">Why it fits</h3>
              {detail.match.reasons.length ? (
                detail.match.reasons.map((reason, i) => (
                  <details className="evidence-row" key={i}>
                    <summary>
                      <CheckCheck size={15} />
                      <span>{reason.reason}</span>
                      <ChevronDown size={14} />
                    </summary>
                    <div className="evidence-pair">
                      <div>
                        <small>JOB EVIDENCE</small>
                        <p>{reason.job_excerpt}</p>
                      </div>
                      <div>
                        <small>
                          PROFILE EVIDENCE · {reason.profile_evidence_id}
                        </small>
                        <p>{reason.profile_excerpt}</p>
                      </div>
                    </div>
                  </details>
                ))
              ) : (
                <p>No shared evidence identified.</p>
              )}
              <div className="two-column">
                <div>
                  <h3 className="detail-section-title">Gaps to consider</h3>
                  {detail.match.gaps.length ? (
                    detail.match.gaps.map((g) => (
                      <p key={g} className="gap-line">
                        {g}
                      </p>
                    ))
                  ) : (
                    <p>
                      Review the original posting for any additional
                      requirements.
                    </p>
                  )}
                </div>
                <div>
                  <h3 className="detail-section-title">Still unknown</h3>
                  {detail.match.unknowns.map((u) => (
                    <p key={u} className="gap-line">
                      {u}
                    </p>
                  ))}
                </div>
              </div>
              <p className="fine-print">
                {detail.match.limitations} {detail.match.model_status}
              </p>
            </>
          ) : (
            <div className="info-callout">
              Approve a profile to generate a match explanation.
            </div>
          )}
          <h3 className="detail-section-title">Timing and sources</h3>
          <p>{publicationLabel(detail.data.publication, timezone)}</p>
          <p>
            First discovered: {dateTime(detail.first_seen_at, timezone)} · Last
            observed: {dateTime(detail.last_seen_at, timezone)}
          </p>
          {detail.sources.map((s, i) => (
            <div className="source-evidence" key={i}>
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.name}
                <ExternalLink size={12} />
              </a>
              <small>
                {publicationLabel(s.publication, timezone)} · precision:{" "}
                {s.publication?.precision || "unknown"} ·{" "}
                {s.publication?.provenance}
              </small>
              {s.updated?.start && (
                <small>
                  Source updated: {dateTime(s.updated.start, timezone)} (not
                  publication)
                </small>
              )}
              {s.received?.start && (
                <small>
                  Email received/imported:{" "}
                  {dateTime(s.received.start, timezone)}
                </small>
              )}
            </div>
          ))}
          <h3 className="detail-section-title">Job description</h3>
          <div className="description-text">
            {detail.data.description ||
              "The imported alert did not include a full description. Open the original posting manually."}
          </div>
          <h3 className="detail-section-title">Your feedback</h3>
          <div className="feedback-buttons">
            {["too junior", "wrong sector", "good match"].map((f) => (
              <button
                className="secondary"
                key={f}
                onClick={() =>
                  act(
                    () =>
                      api(`/jobs/${detail.id}`, {
                        method: "PATCH",
                        body: JSON.stringify({ feedback: f }),
                      }),
                    "Feedback recorded. Scoring preferences stay under your control.",
                  )
                }
              >
                {f}
              </button>
            ))}
          </div>
          <details className="manual-resolution">
            <summary>Availability and duplicate records</summary>
            <div className="two-column">
              <label>
                Confirm availability
                <select
                  value={detail.availability}
                  onChange={(e) => {
                    const availability = e.target.value;
                    act(
                      () =>
                        api(`/jobs/${detail.id}`, {
                          method: "PATCH",
                          body: JSON.stringify({ availability }),
                        }),
                      "Availability updated.",
                    );
                    setDetail({ ...detail, availability });
                  }}
                >
                  {["open", "closed", "unverified"].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              <label>
                Merge a duplicate into this job
                <select
                  defaultValue=""
                  onChange={(e) => {
                    const duplicate = e.target.value;
                    if (duplicate)
                      act(
                        () =>
                          api(`/jobs/${detail.id}/merge/${duplicate}`, {
                            method: "POST",
                          }),
                        "Records merged, preserving source links and delivery history.",
                      );
                  }}
                >
                  <option value="">Choose duplicate…</option>
                  {jobs
                    .filter((j) => j.id !== detail.id)
                    .map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.company}: {j.title}
                      </option>
                    ))}
                </select>
              </label>
            </div>
          </details>
        </Modal>
      )}
      {importOpen && (
        <ImportDialog
          busy={busy}
          act={act}
          close={() => setImportOpen(false)}
        />
      )}
      {sourceOpen && (
        <SourceDialog
          source={sourceOpen}
          busy={busy}
          act={act}
          close={() => setSourceOpen(null)}
        />
      )}
    </div>
  );
}

type Action = (
  action: () => Promise<unknown>,
  message: string,
) => Promise<boolean>;
function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">
          <span className="small-line" />
          {eyebrow}
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

function ProfilePage({
  profiles,
  busy,
  act,
}: {
  profiles: Profile[];
  busy: boolean;
  act: Action;
}) {
  const [editing, setEditing] = useState<Profile | null>(null);
  const [paste, setPaste] = useState("");
  const selected = editing || profiles[0];
  const upload = (file: File) => {
    const data = new FormData();
    data.append("file", file);
    act(async () => {
      const p = await api<Profile>("/profiles/upload", {
        method: "POST",
        body: data,
      });
      setEditing(p);
    }, "Résumé extracted locally. Review the excerpts before approval.");
  };
  return (
    <>
      <PageHeading
        eyebrow="EXPERIENCE IS YOUR FOUNDATION"
        title="Your story. In evidence."
        description="Review what matters to your search, and approve only what is accurate."
      />
      <div className="two-column profile-layout">
        <section className="card profile-editor">
          <div className="section-title">
            <h2>Candidate evidence</h2>
            {selected && (
              <Badge tone={selected.approved ? "green" : "amber"}>
                {selected.approved
                  ? `Approved · v${selected.id}`
                  : "Draft · review required"}
              </Badge>
            )}
          </div>
          {selected ? (
            <>
              <label>
                Profile label
                <input
                  value={selected.data.label}
                  onChange={(e) =>
                    setEditing({
                      ...selected,
                      data: { ...selected.data, label: e.target.value },
                    })
                  }
                />
              </label>
              {selected.data.evidence.map((item, i) => (
                <div className="profile-evidence" key={item.id}>
                  <div className="evidence-label">
                    <span>
                      {item.id} · {item.category}
                    </span>
                    <button
                      className="icon-button"
                      aria-label={`Remove evidence ${item.id}`}
                      onClick={() =>
                        setEditing({
                          ...selected,
                          data: {
                            ...selected.data,
                            evidence: selected.data.evidence.filter(
                              (_, index) => i !== index,
                            ),
                          },
                        })
                      }
                    >
                      <X size={14} />
                    </button>
                  </div>
                  <textarea
                    aria-label={`Evidence ${item.id}`}
                    rows={3}
                    value={item.text}
                    onChange={(e) =>
                      setEditing({
                        ...selected,
                        data: {
                          ...selected.data,
                          evidence: selected.data.evidence.map((v, index) =>
                            index === i
                              ? {
                                  ...v,
                                  text: e.target.value,
                                  source: "user correction",
                                }
                              : v,
                          ),
                        },
                      })
                    }
                  />
                  <small>Source: {item.source}</small>
                </div>
              ))}
              <button
                className="secondary"
                onClick={() =>
                  setEditing({
                    ...selected,
                    data: {
                      ...selected.data,
                      evidence: [
                        ...selected.data.evidence,
                        {
                          id: `user-${Date.now()}`,
                          text: "",
                          source: "user input",
                          category: "experience",
                        },
                      ],
                    },
                  })
                }
              >
                <Plus size={15} />
                Add evidence
              </button>
              <div className="approval-bar">
                <p>
                  <ShieldCheck size={15} /> Edits create a new version. Old
                  matching results remain auditable.
                </p>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    act(async () => {
                      const p = await api<Profile>(`/profiles/${selected.id}`, {
                        method: "PUT",
                        body: JSON.stringify(selected.data),
                      });
                      await api(`/profiles/${p.id}/approve`, {
                        method: "POST",
                      });
                      setEditing(null);
                    }, "Profile approved. Jobs re-scored without resending previous discovery alerts.")
                  }
                >
                  <Check size={16} />
                  Save & approve
                </button>
              </div>
            </>
          ) : (
            <Empty title="Add your experience">
              Upload a résumé or paste text to create your first profile.
            </Empty>
          )}
        </section>
        <aside className="profile-inputs">
          <section className="card">
            <h3>Bring your résumé</h3>
            <p>
              PDF, DOCX or UTF-8 text, up to 10 MB. Files are processed locally
              and are not retained.
            </p>
            <label className="upload-zone">
              <Upload size={25} />
              <strong>Choose a résumé</strong>
              <span>PDF, DOCX, TXT</span>
              <input
                type="file"
                aria-label="Upload résumé"
                accept=".pdf,.docx,.txt"
                disabled={busy}
                onChange={(e) =>
                  e.target.files?.[0] && upload(e.target.files[0])
                }
              />
            </label>
            <label>
              Or paste résumé text
              <textarea
                rows={7}
                value={paste}
                onChange={(e) => setPaste(e.target.value)}
                placeholder="Paste experience and qualifications…"
              />
            </label>
            <button
              className="secondary full-width"
              disabled={busy || paste.trim().length < 10}
              onClick={() =>
                act(async () => {
                  const p = await api<Profile>("/profiles/paste", {
                    method: "POST",
                    body: JSON.stringify({ text: paste }),
                  });
                  setEditing(p);
                  setPaste("");
                }, "Draft profile created. Review evidence before approval.")
              }
            >
              Extract evidence <ArrowRight size={15} />
            </button>
          </section>
          <div className="info-callout vertical">
            <ShieldCheck size={21} />
            <h3>You stay in control</h3>
            <p>
              Missing facts remain unknown. Candidate text is not sent to an
              external model unless you enable it and consent in Settings.
            </p>
            <p>
              Work authorization, salary, and sponsorship are never inferred
              from your location or nationality.
            </p>
          </div>
          {profiles.length > 1 && (
            <section className="card">
              <h3>Profile history</h3>
              {profiles.map((p) => (
                <button
                  className="version-row"
                  key={p.id}
                  onClick={() => setEditing(p)}
                >
                  <span>Version {p.id}</span>
                  <Badge tone={p.approved ? "green" : "amber"}>
                    {p.approved ? "Approved" : "Draft"}
                  </Badge>
                </button>
              ))}
            </section>
          )}
        </aside>
      </div>
    </>
  );
}

function SettingsPage({
  settings,
  busy,
  act,
}: {
  settings: AppSettings;
  busy: boolean;
  act: Action;
}) {
  const [draft, setDraft] = useState<AppSettings>(settings);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) =>
    setDraft({ ...draft, [key]: value });
  const save = () =>
    act(
      () =>
        api("/settings", {
          method: "PATCH",
          body: JSON.stringify(
            Object.fromEntries(
              Object.entries(draft).filter(
                ([key]) =>
                  ![
                    "demo_mode",
                    "smtp_configured",
                    "model_configured",
                    "llm_provider",
                    "llm_model",
                  ].includes(key),
              ),
            ),
          ),
        }),
      "Preferences saved. Relevant scoring changes are applied to existing jobs.",
    );
  return (
    <>
      <PageHeading
        eyebrow="A SEARCH THAT FITS YOUR LIFE"
        title="Set your direction."
        description="Your regions, priorities, delivery preferences, and spending limits."
        action={
          <button className="primary" disabled={busy} onClick={save}>
            <Check size={16} />
            Save preferences
          </button>
        }
      />
      <div className="settings-grid">
        <section className="card">
          <h2>Geography & roles</h2>
          <p>
            Preferred work countries are editable hard location filters. Unknown
            locations remain visible.
          </p>
          <div className="country-checkboxes">
            {Object.entries(countries).map(([code, name]) => (
              <label key={code}>
                <input
                  type="checkbox"
                  checked={draft.countries.includes(code)}
                  onChange={(e) =>
                    update(
                      "countries",
                      e.target.checked
                        ? [...draft.countries, code]
                        : draft.countries.filter((c) => c !== code),
                    )
                  }
                />
                {name}
              </label>
            ))}
          </div>
          <label>
            Target title aliases
            <textarea
              rows={5}
              value={draft.role_aliases.join("\n")}
              onChange={(e) =>
                update(
                  "role_aliases",
                  e.target.value.split("\n").filter(Boolean),
                )
              }
            />
          </label>
          <label>
            Excluded title phrases
            <textarea
              rows={3}
              value={draft.exclusions.join("\n")}
              onChange={(e) =>
                update("exclusions", e.target.value.split("\n").filter(Boolean))
              }
            />
          </label>
          <p className="fine-print">
            Titles are discovery signals. Executive scope and evidence determine
            fit.
          </p>
        </section>
        <section className="card">
          <h2>Matching preferences</h2>
          <p>Weights must total 100. Fit scores are heuristic rankings.</p>
          {Object.entries(draft.weights).map(([key, value]) => (
            <label className="weight-row" key={key}>
              {dimensionNames[key]}
              <input
                type="number"
                min="0"
                max="100"
                value={value}
                onChange={(e) =>
                  update("weights", {
                    ...draft.weights,
                    [key]: Number(e.target.value),
                  })
                }
              />
            </label>
          ))}
          <div className="two-column">
            <label>
              High-match threshold
              <input
                type="number"
                min="0"
                max="100"
                value={draft.high_threshold}
                onChange={(e) =>
                  update("high_threshold", Number(e.target.value))
                }
              />
            </label>
            <label>
              Review threshold
              <input
                type="number"
                min="0"
                max="100"
                value={draft.review_threshold}
                onChange={(e) =>
                  update("review_threshold", Number(e.target.value))
                }
              />
            </label>
          </div>
          <hr />
          <h3>Optional model matching</h3>
          <Badge tone={settings.model_configured ? "green" : "muted"}>
            {settings.model_configured
              ? `${settings.llm_provider} · ${settings.llm_model}`
              : "Provider credentials and prices required"}
          </Badge>
          <p>
            Selected candidate evidence and job descriptions are sent to the
            configured provider. Contact details and the raw résumé are
            excluded. Deterministic matching is always available.
          </p>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={draft.external_model_consent}
              onChange={(e) =>
                update("external_model_consent", e.target.checked)
              }
            />
            I consent to sending selected evidence to the model provider.
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={draft.llm_enabled}
              onChange={(e) => update("llm_enabled", e.target.checked)}
            />
            Enable model matching
          </label>
          <label>
            Monthly model budget (USD)
            <input
              type="number"
              min="0"
              step="1"
              value={draft.monthly_budget_usd}
              onChange={(e) =>
                update("monthly_budget_usd", Number(e.target.value))
              }
            />
          </label>
        </section>
        <section className="card">
          <h2>Notifications & timing</h2>
          {settings.demo_mode && (
            <div className="info-callout">
              Demo mode creates previews only, even if SMTP is configured.
            </div>
          )}
          <label>
            Recipient email
            <input
              type="email"
              value={draft.recipient}
              onChange={(e) => update("recipient", e.target.value)}
              placeholder="you@example.com"
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={draft.notifications_enabled}
              onChange={(e) =>
                update("notifications_enabled", e.target.checked)
              }
            />
            Enable notifications to this recipient
          </label>
          <label>
            Display timezone
            <input
              value={draft.timezone}
              onChange={(e) => update("timezone", e.target.value)}
            />
          </label>
          <div className="two-column">
            <label>
              Daily digest hour
              <input
                type="number"
                min="0"
                max="23"
                value={draft.digest_hour}
                onChange={(e) => update("digest_hour", Number(e.target.value))}
              />
            </label>
            <label>
              Quiet hours start
              <input
                type="number"
                min="0"
                max="23"
                value={draft.quiet_start ?? ""}
                onChange={(e) =>
                  update(
                    "quiet_start",
                    e.target.value === "" ? null : Number(e.target.value),
                  )
                }
              />
            </label>
            <label>
              Quiet hours end
              <input
                type="number"
                min="0"
                max="23"
                value={draft.quiet_end ?? ""}
                onChange={(e) =>
                  update(
                    "quiet_end",
                    e.target.value === "" ? null : Number(e.target.value),
                  )
                }
              />
            </label>
          </div>
          <p className="fine-print">
            Hours use the selected timezone. Blank or equal quiet-hour values
            disable quiet hours.
          </p>
          <button
            className="secondary"
            disabled={busy}
            onClick={() =>
              act(
                () => api("/notifications/test", { method: "POST" }),
                settings.demo_mode
                  ? "Preview created in Activity."
                  : "Test processed for the saved recipient. Check Activity for the delivery result.",
              )
            }
          >
            <Mail size={15} />
            {settings.demo_mode
              ? "Preview test notification"
              : "Send test to saved recipient"}
          </button>
        </section>
        <section className="card">
          <h2>Your data</h2>
          <p>
            Raw résumé uploads are never stored. Email metadata and scan logs
            have configurable retention. Backups expire separately.
          </p>
          <div className="two-column">
            <label>
              Email metadata retention (days)
              <input
                type="number"
                min="1"
                max="3650"
                value={draft.email_retention_days}
                onChange={(e) =>
                  update("email_retention_days", Number(e.target.value))
                }
              />
            </label>
            <label>
              Scan log retention (days)
              <input
                type="number"
                min="1"
                max="3650"
                value={draft.log_retention_days}
                onChange={(e) =>
                  update("log_retention_days", Number(e.target.value))
                }
              />
            </label>
          </div>
          <button
            className="secondary"
            onClick={() =>
              act(async () => {
                const data = await api("/export");
                const url = URL.createObjectURL(
                  new Blob([JSON.stringify(data, null, 2)], {
                    type: "application/json",
                  }),
                );
                const a = document.createElement("a");
                a.href = url;
                a.download = "fieldwork-export.json";
                a.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
              }, "Workspace exported. Keep the downloaded file private.")
            }
          >
            <ArrowDownToLine size={16} />
            Export results & profile
          </button>
          <hr />
          <h3>Delete candidate data</h3>
          <p>
            Removes profile versions, match caches, imported email metadata, and
            notifications. Jobs and source configurations remain.
          </p>
          {confirmDelete ? (
            <div className="confirm-delete">
              <strong>Delete all candidate profile data?</strong>
              <button
                className="danger"
                disabled={busy}
                onClick={() =>
                  act(
                    () => api("/profiles", { method: "DELETE" }),
                    "Candidate data deleted. Backups follow the documented expiration policy.",
                  )
                }
              >
                Yes, delete candidate data
              </button>
              <button
                className="text-button"
                onClick={() => setConfirmDelete(false)}
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              className="danger-outline"
              onClick={() => setConfirmDelete(true)}
            >
              Delete candidate data
            </button>
          )}
        </section>
      </div>
    </>
  );
}

function ImportDialog({
  busy,
  act,
  close,
}: {
  busy: boolean;
  act: Action;
  close: () => void;
}) {
  const [mode, setMode] = useState("email");
  const [form, setForm] = useState({
    title: "",
    company: "",
    url: "",
    description: "",
    location: "",
    country: "",
  });
  return (
    <Modal title="Import opportunities" onClose={close}>
      <div className="tabs">
        <button
          className={mode === "email" ? "selected" : ""}
          onClick={() => setMode("email")}
        >
          Job-alert email
        </button>
        <button
          className={mode === "manual" ? "selected" : ""}
          onClick={() => setMode("manual")}
        >
          Manual vacancy
        </button>
      </div>
      {mode === "email" ? (
        <>
          <p>
            Upload a job-alert email saved as .eml. Only links and facts in your
            message are imported. LinkedIn links are never visited
            automatically.
          </p>
          <label className="upload-zone">
            <Mail size={28} />
            <strong>Choose an .eml file</strong>
            <span>Up to 10 MB · partial descriptions stay provisional</span>
            <input
              type="file"
              aria-label="Upload job-alert email"
              accept=".eml"
              disabled={busy}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const data = new FormData();
                data.append("file", file);
                act(
                  () => api("/imports/email", { method: "POST", body: data }),
                  "Email processed. Imported matches are labeled limited evidence.",
                );
              }}
            />
          </label>
        </>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            act(
              () =>
                api("/imports/jobs", {
                  method: "POST",
                  body: JSON.stringify([
                    {
                      external_id: form.url,
                      title: form.title,
                      company: form.company,
                      url: form.url,
                      description: form.description,
                      locations: form.location ? [form.location] : [],
                      countries: form.country ? [form.country] : [],
                      provisional: form.description.length < 240,
                    },
                  ]),
                }),
              "Vacancy imported. The first import establishes a quiet baseline.",
            );
          }}
        >
          <div className="two-column">
            {(["title", "company", "url", "location"] as const).map((key) => (
              <label key={key}>
                {key === "url"
                  ? "Original vacancy URL"
                  : key[0].toUpperCase() + key.slice(1)}
                <input
                  required={key !== "location"}
                  type={key === "url" ? "url" : "text"}
                  value={form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                />
              </label>
            ))}
          </div>
          <label>
            Confirmed work country
            <select
              value={form.country}
              onChange={(e) => setForm({ ...form, country: e.target.value })}
            >
              <option value="">Unknown</option>
              {Object.entries(countries).map(([code, name]) => (
                <option key={code} value={code}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Job description
            <textarea
              rows={7}
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
            />
          </label>
          <button className="primary" disabled={busy}>
            Import vacancy <ArrowRight size={15} />
          </button>
        </form>
      )}
    </Modal>
  );
}

function SourceDialog({
  source,
  busy,
  act,
  close,
}: {
  source: Source | "new";
  busy: boolean;
  act: Action;
  close: () => void;
}) {
  const existing = source === "new" ? null : source;
  const [name, setName] = useState(existing?.name || "");
  const [company, setCompany] = useState(existing?.company || "");
  const [kind, setKind] = useState(
    existing?.kind === "unsupported" ? "html" : existing?.kind || "greenhouse",
  );
  const [url, setUrl] = useState(existing?.url || "");
  const [interval, setInterval] = useState(existing?.interval_minutes || 60);
  const [board, setBoard] = useState(String(existing?.config.board || ""));
  const [region, setRegion] = useState(
    String(existing?.config.region || "global"),
  );
  const [reviewed, setReviewed] = useState(
    Boolean(existing?.config.access_reviewed),
  );
  const [reviewNotes, setReviewNotes] = useState(
    String(existing?.config.access_notes || ""),
  );
  const [itemSelector, setItemSelector] = useState(
    String(existing?.config.item_selector || ""),
  );
  const [titleSelector, setTitleSelector] = useState(
    String(existing?.config.title_selector || ""),
  );
  const [linkSelector, setLinkSelector] = useState(
    String(existing?.config.link_selector || ""),
  );
  const [descriptionSelector, setDescriptionSelector] = useState(
    String(existing?.config.description_selector || ""),
  );
  const [nextSelector, setNextSelector] = useState(
    String(existing?.config.next_selector || ""),
  );
  const [emptySelector, setEmptySelector] = useState(
    String(existing?.config.empty_selector || ""),
  );
  const [singlePage, setSinglePage] = useState(
    Boolean(existing?.config.single_page),
  );
  return (
    <Modal
      title={existing ? "Configure source" : "Add a career source"}
      onClose={close}
    >
      <p>
        Use an official board identifier or an explicitly configured public
        page. Passing a connection test is required before enabling a source.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const config = {
            ...(existing?.config || {}),
            board,
            region,
            access_reviewed: reviewed,
            access_notes: reviewNotes,
            item_selector: itemSelector,
            title_selector: titleSelector,
            link_selector: linkSelector,
            description_selector: descriptionSelector,
            next_selector: nextSelector,
            empty_selector: emptySelector,
            single_page: singlePage,
          };
          act(async () => {
            const result = await api<Source>(
              existing ? `/sources/${existing.id}` : "/sources",
              {
                method: existing ? "PATCH" : "POST",
                body: JSON.stringify({
                  name,
                  company,
                  kind,
                  url,
                  interval_minutes: interval,
                  config,
                }),
              },
            );
            await api(`/sources/${result.id}/test`, { method: "POST" });
          }, "Source saved and tested. Review the capability result before enabling.");
        }}
      >
        <div className="two-column">
          <label>
            Source name
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            Employer
            <input
              required
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />
          </label>
        </div>
        <label>
          Connector
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="greenhouse">Greenhouse public board</option>
            <option value="lever">Lever public postings</option>
            <option value="html">Configured public HTML / JSON-LD</option>
            {existing?.kind === "demo" && (
              <option value="demo">Synthetic demo</option>
            )}
          </select>
        </label>
        <label>
          Official careers URL
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required={kind === "html"}
          />
        </label>
        {["greenhouse", "lever"].includes(kind) && (
          <label>
            External board identifier
            <input
              required
              value={board}
              onChange={(e) => setBoard(e.target.value)}
              placeholder="company-board-name"
            />
          </label>
        )}
        {kind === "lever" && (
          <label>
            Lever endpoint
            <select value={region} onChange={(e) => setRegion(e.target.value)}>
              <option value="global">Global</option>
              <option value="eu">EU</option>
            </select>
          </label>
        )}
        {kind === "html" && (
          <>
            <div className="info-callout">
              JSON-LD JobPosting is detected automatically. For other pages,
              configure stable selectors and pagination. A generic parser does
              not support every ATS.
            </div>
            <div className="two-column">
              {[
                ["Job row selector", itemSelector, setItemSelector],
                ["Title selector", titleSelector, setTitleSelector],
                ["Link selector", linkSelector, setLinkSelector],
                [
                  "Description selector",
                  descriptionSelector,
                  setDescriptionSelector,
                ],
                ["Next-page link selector", nextSelector, setNextSelector],
                [
                  "Explicit empty-state selector",
                  emptySelector,
                  setEmptySelector,
                ],
              ].map(([label, value, setter]) => (
                <label key={String(label)}>
                  {String(label)}
                  <input
                    value={String(value)}
                    onChange={(e) =>
                      (setter as (v: string) => void)(e.target.value)
                    }
                  />
                </label>
              ))}
            </div>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={singlePage}
                onChange={(e) => setSinglePage(e.target.checked)}
              />
              This configured page contains the complete board on one page
            </label>
          </>
        )}
        <label>
          Scan interval (minutes)
          <input
            type="number"
            min="15"
            max="10080"
            value={interval}
            onChange={(e) => setInterval(Number(e.target.value))}
          />
        </label>
        <label>
          Robots, terms, and access review notes
          <textarea
            rows={3}
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            placeholder="Record URLs reviewed, date and access basis…"
          />
        </label>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={reviewed}
            onChange={(e) => setReviewed(e.target.checked)}
          />
          I reviewed robots and terms/access permission for this source
        </label>
        <button className="primary" disabled={busy}>
          Save & test connection <ArrowRight size={15} />
        </button>
      </form>
    </Modal>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
