export interface Evidence {
  id: string;
  text: string;
  category: string;
  source: string;
}
export interface Profile {
  id: number;
  approved: boolean;
  data: {
    label: string;
    evidence: Evidence[];
    notes?: string;
    [key: string]: unknown;
  };
}
export interface Timestamp {
  raw: string | null;
  precision: string;
  start: string | null;
  end: string | null;
  provenance: string;
  timezone: string;
}
export interface Reason {
  dimension: string;
  reason: string;
  job_excerpt: string;
  profile_excerpt: string;
  profile_evidence_id: string;
}
export interface MatchResult {
  score: number;
  dimensions: Record<string, number>;
  reasons: Reason[];
  gaps: string[];
  unknowns: string[];
  hard_filters: string[];
  provisional: boolean;
  method: string;
  recommendation: string;
  limitations: string;
  model_status?: string;
}
export interface Job {
  id: number;
  title: string;
  company: string;
  url: string;
  availability: string;
  candidate_status: string;
  feedback: string[];
  first_seen_at: string;
  last_seen_at: string;
  match: MatchResult | null;
  data: {
    description: string;
    locations: string[];
    countries: string[];
    work_mode: string;
    employment_type: string;
    publication: Timestamp;
    updated: Timestamp;
    provisional: boolean;
    demo: boolean;
  };
  sources: {
    id: number;
    name: string;
    kind: string;
    url: string;
    publication: Timestamp;
    updated: Timestamp;
    received: Timestamp;
    first_seen_at: string;
  }[];
}
export interface Source {
  id: number;
  name: string;
  company: string;
  kind: string;
  url: string;
  enabled: boolean;
  interval_minutes: number;
  last_success: string | null;
  next_run: string;
  stale: boolean;
  last_error: string | null;
  baseline_complete: boolean;
  config: Record<string, unknown>;
  capability: {
    supported?: boolean;
    error?: string;
    note?: string;
    archived?: boolean;
    tested_at?: string;
    count?: number;
    complete?: boolean;
  };
}
export interface Overview {
  demo: boolean;
  total_jobs: number;
  high_matches: number;
  saved: number;
  enabled_sources: number;
  total_sources: number;
  stale_sources: number;
  profile_approved: boolean;
  worker: { last_tick: string } | null;
  model_cost_usd: number;
  budget_usd: number;
  timezone: string;
}
export interface AppSettings {
  countries: string[];
  weights: Record<string, number>;
  high_threshold: number;
  review_threshold: number;
  timezone: string;
  digest_hour: number;
  quiet_start: number | null;
  quiet_end: number | null;
  notifications_enabled: boolean;
  recipient: string;
  llm_enabled: boolean;
  external_model_consent: boolean;
  monthly_budget_usd: number;
  email_retention_days: number;
  log_retention_days: number;
  exclusions: string[];
  role_aliases: string[];
  demo_mode: boolean;
  smtp_configured: boolean;
  model_configured: boolean;
  llm_provider: string;
  llm_model: string;
}
export interface Run {
  id: number;
  source_id: number;
  started_at: string;
  ended_at: string | null;
  status: string;
  complete: boolean;
  count: number;
  new_count: number;
  error: string | null;
  stats: { warnings?: string[] };
}
export interface Notification {
  id: number;
  type: string;
  status: string;
  created_at: string;
  due_at: string;
  attempts: number;
  body: string;
}
export interface Activity {
  runs: Run[];
  notifications: Notification[];
  delivery_attempts: {
    notification_id: number;
    status: string;
    error: string | null;
    provider_id: string | null;
  }[];
  model_usage: {
    id: number;
    status: string;
    reserved_usd: number;
    actual_usd: number | null;
    tokens: number;
  }[];
}
