export interface ApiError {
  message: string; // Map the top level "error" string to message for standard Error compatibility
  details?: Record<string, string[]>;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  is_verified: boolean;
  is_2fa_enabled: boolean;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  owner: number;
  is_active: boolean;
  role?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceCurrentResponse {
  workspace: Workspace;
  role: string;
  membership_id: number | null;
}

export interface Project {
  id: number;
  name: string;
  description: string;
  user: number;
  created_at: string;
  updated_at: string;
}

export interface Subscription {
  id: string | null;
  status: string;
  price_id: string | null;
  cancel_at_period_end: boolean;
}

export interface SubscriptionResponse {
  has_active_subscription: boolean;
  subscription: Subscription | null;
}

export interface DashboardStats {
  total_users: number;
  active_users: number;
  verified_users: number;
  registrations_30d: number;
}

export interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

export interface EntitlementsResponse {
  plan: string;
  features: string[];
  limits: Record<string, number>;
}
