const API_URL = import.meta.env.VITE_API_URL ?? `http://${window.location.hostname}:8000`;

export type User = {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export type Account = {
  id: string;
  account_number: string;
  currency: string;
  status: string;
  available_balance: string;
  created_at: string;
};

export type Transaction = {
  transaction_id: string;
  type: string;
  amount: string;
  currency: string;
  status: string;
  replayed: boolean;
};

export type StatementEntry = {
  transaction_id: string | null;
  action: string;
  amount: string | null;
  result: string;
  reason: string | null;
  resulting_balance: string | null;
  occurred_at: string;
};

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error(`Cannot reach Balance Vault API at ${API_URL}. Start Uvicorn on port 8000.`);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: (token: string) => request<User>("/auth/me", {}, token),
  accounts: (token: string) => request<Account[]>("/accounts", {}, token),
  createAccount: (token: string, currency: string) =>
    request<Account>("/accounts", {
      method: "POST",
      body: JSON.stringify({ currency }),
    }, token),
  statement: (token: string, accountId: string) =>
    request<StatementEntry[]>(`/accounts/${accountId}/statement`, {}, token),
  transactions: (token: string) =>
    request<{ items: Transaction[] }>("/transactions?limit=20&offset=0", {}, token),
  deposit: (token: string, accountId: string, amount: string, key: string) =>
    request<Transaction>("/transactions/deposit", {
      method: "POST",
      headers: { "Idempotency-Key": key },
      body: JSON.stringify({ account_id: accountId, amount }),
    }, token),
  withdraw: (token: string, accountId: string, amount: string, key: string) =>
    request<Transaction>("/transactions/withdraw", {
      method: "POST",
      headers: { "Idempotency-Key": key },
      body: JSON.stringify({ account_id: accountId, amount }),
    }, token),
  transfer: (
    token: string,
    sourceAccountId: string,
    destinationAccountId: string,
    amount: string,
    key: string,
  ) =>
    request<Transaction>("/transactions/transfer", {
      method: "POST",
      headers: { "Idempotency-Key": key },
      body: JSON.stringify({
        source_account_id: sourceAccountId,
        destination_account_id: destinationAccountId,
        amount,
      }),
    }, token),
};
