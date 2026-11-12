import { useEffect, useMemo, useState } from "react";
import type * as React from "react";
import {
  ArrowDownLeft, ArrowLeftRight, ArrowUpRight, ChevronRight, CircleDollarSign,
  ClipboardList, CreditCard, LogOut, Plus, ShieldCheck, Sparkles, Wallet,
} from "lucide-react";
import { Account, api, StatementEntry, Transaction, User } from "./api";

type AuthMode = "login" | "register";
type Action = "deposit" | "withdraw" | "transfer" | null;

const TOKEN_KEY = "vaultwise_token";
const LEGACY_TOKEN_KEYS = ["balance_vault_token", "ledgerline_token"];

function getStoredToken() {
  const token = localStorage.getItem(TOKEN_KEY)
    ?? LEGACY_TOKEN_KEYS.map((key) => localStorage.getItem(key)).find(Boolean)
    ?? null;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  LEGACY_TOKEN_KEYS.forEach((key) => localStorage.removeItem(key));
  return token;
}

function money(value: string | number, currency = "INR") {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(Number(value));
}

function App() {
  const [token, setToken] = useState(getStoredToken);
  const [user, setUser] = useState<User | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [statement, setStatement] = useState<StatementEntry[]>([]);
  const [selectedAccount, setSelectedAccount] = useState("");
  const [action, setAction] = useState<Action>(null);
  const [loading, setLoading] = useState(Boolean(token));
  const [error, setError] = useState("");

  const refresh = async (activeToken: string) => {
    const [currentUser, currentAccounts, transactionPage] = await Promise.all([
      api.me(activeToken), api.accounts(activeToken), api.transactions(activeToken),
    ]);
    setUser(currentUser);
    setAccounts(currentAccounts);
    setTransactions(transactionPage.items);
    if (currentAccounts.length && !selectedAccount) {
      setSelectedAccount(currentAccounts[0].id);
      setStatement(await api.statement(activeToken, currentAccounts[0].id));
    }
  };

  useEffect(() => {
    if (!token) return;
    refresh(token).catch((cause: Error) => {
      localStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setError(cause.message);
    }).finally(() => setLoading(false));
  }, [token]);

  const totalBalance = useMemo(
    () => accounts.reduce((sum, account) => sum + Number(account.available_balance), 0),
    [accounts],
  );

  const selectAccount = async (id: string) => {
    setSelectedAccount(id);
    if (token) setStatement(await api.statement(token, id));
  };

  const signOut = () => {
    localStorage.removeItem(TOKEN_KEY);
    LEGACY_TOKEN_KEYS.forEach((key) => localStorage.removeItem(key));
    setToken(null);
    setUser(null);
  };

  if (!token) return <AuthScreen mode="login" onAuthenticated={(value) => {
    localStorage.setItem(TOKEN_KEY, value);
    setToken(value);
  }} />;
  if (loading || !user) return <div className="loading-screen"><Sparkles /> Loading your secure workspace...</div>;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><CircleDollarSign size={23} /></div><span>VaultWise</span></div>
        <div className="side-label">Workspace</div>
        <button className="nav-item active"><Wallet size={18} /> Overview</button>
        <button className="nav-item" onClick={() => document.getElementById("accounts")?.scrollIntoView()}><CreditCard size={18} /> Accounts</button>
        <button className="nav-item" onClick={() => document.getElementById("activity")?.scrollIntoView()}><ClipboardList size={18} /> Activity</button>
        <div className="sidebar-bottom">
          <div className="security-badge"><ShieldCheck size={18} /><div><strong>Protected</strong><small>Bank-grade controls active</small></div></div>
          <button className="nav-item logout" onClick={signOut}><LogOut size={18} /> Sign out</button>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar"><div><p className="eyebrow">PERSONAL FINANCE</p><h1>Good afternoon, {user.email.split("@")[0]}</h1></div><div className="avatar">{user.email[0].toUpperCase()}</div></header>
        {error && <div className="alert error">{error}<button onClick={() => setError("")}>×</button></div>}
        <section className="hero-card">
          <div><p className="muted">Total available balance</p><div className="total-balance">{money(totalBalance)}</div><p className="hero-note"><ShieldCheck size={15} /> Your funds are protected by double-entry accounting</p></div>
          <div className="hero-orb"><CircleDollarSign size={100} /></div>
        </section>
        <section className="quick-actions">
          <ActionButton icon={<ArrowDownLeft />} label="Deposit" onClick={() => setAction("deposit")} />
          <ActionButton icon={<ArrowUpRight />} label="Withdraw" onClick={() => setAction("withdraw")} />
          <ActionButton icon={<ArrowLeftRight />} label="Transfer" onClick={() => setAction("transfer")} />
          <ActionButton icon={<Plus />} label="New account" onClick={async () => {
            if (token) { await api.createAccount(token, "INR"); await refresh(token); }
          }} />
        </section>
        <section id="accounts" className="section"><SectionTitle title="Your accounts" action="Create account" onAction={async () => { if (token) { await api.createAccount(token, "INR"); await refresh(token); } }} />
          <div className="account-grid">{accounts.map((account) => <button className={`account-card ${selectedAccount === account.id ? "selected" : ""}`} key={account.id} onClick={() => selectAccount(account.id)}><div className="card-top"><span className="account-icon"><CreditCard size={19} /></span><span className="status-dot">Active</span></div><p>{account.account_number}</p><strong>{money(account.available_balance, account.currency)}</strong><small>{account.currency} account <ChevronRight size={14} /></small></button>)}</div>
        </section>
        <section id="activity" className="section split-section"><div className="panel"><SectionTitle title="Recent activity" action="View all" onAction={() => document.getElementById("activity")?.scrollIntoView()} /><div className="activity-list">{transactions.length ? transactions.slice(0, 6).map((transaction) => <div className="activity-row" key={transaction.transaction_id}><div className={`activity-icon ${transaction.type}`}><ActivityIcon type={transaction.type} /></div><div className="activity-info"><strong>{transaction.type.replace("_", " ")}</strong><small>{transaction.status} {transaction.replayed ? "• replayed safely" : ""}</small></div><strong className={transaction.type === "withdrawal" ? "negative" : "positive"}>{transaction.type === "withdrawal" ? "-" : "+"}{money(transaction.amount, transaction.currency)}</strong></div>) : <EmptyState text="Your transactions will appear here." />}</div></div>
          <div className="panel"><SectionTitle title="Statement" action="Refresh" onAction={() => selectedAccount && token && selectAccount(selectedAccount)} /><div className="statement-list">{statement.length ? statement.slice(-5).reverse().map((entry, index) => <div className="statement-row" key={`${entry.occurred_at}-${index}`}><div><strong>{entry.action}</strong><small>{new Date(entry.occurred_at).toLocaleString()}</small></div><span className={entry.result === "posted" ? "positive" : "negative"}>{entry.result === "posted" ? "+" : ""}{entry.amount ? money(entry.amount) : "—"}</span></div>) : <EmptyState text="Select an account to see its statement." />}</div></div>
        </section>
        <footer className="section-title"><strong>VaultWise</strong><span>Secure money movement</span></footer>
      </main>
      {action && <MovementModal action={action} accounts={accounts} token={token} onClose={() => setAction(null)} onComplete={async () => { setAction(null); await refresh(token); if (selectedAccount) setStatement(await api.statement(token, selectedAccount)); }} />}
    </div>
  );
}

function AuthScreen({ mode: initialMode, onAuthenticated }: { mode: AuthMode; onAuthenticated: (token: string) => void }) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError("");
    try { if (mode === "register") await api.register(email, password); const result = await api.login(email, password); onAuthenticated(result.access_token); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to continue"); }
  };
  return <div className="auth-page"><div className="auth-decoration"><div className="brand light"><div className="brand-mark"><CircleDollarSign size={23} /></div><span>VaultWise</span></div><div className="auth-quote"><h2>Money movement,<br /><em>made trustworthy.</em></h2><p>One secure workspace for every balance, transfer, and financial decision.</p><div className="trust-line"><ShieldCheck size={18} /> Double-entry accounting · Immutable audit trails</div></div></div><div className="auth-card"><div className="mobile-brand"><div className="brand"><div className="brand-mark"><CircleDollarSign size={23} /></div><span>VaultWise</span></div></div><p className="eyebrow">SECURE FINANCE PLATFORM</p><h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1><p className="form-subtitle">{mode === "login" ? "Sign in to your secure VaultWise workspace." : "Start moving money with confidence."}</p>{error && <div className="alert error">{error}</div>}<form onSubmit={submit}><label>Email address<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></label><label>Password<input type="password" required minLength={mode === "register" ? 12 : 1} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••••••" /></label><button className="primary-button" type="submit">{mode === "login" ? "Sign in securely" : "Create account"} <ChevronRight size={17} /></button></form><p className="switch-auth">{mode === "login" ? "New to VaultWise?" : "Already have an account?"} <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>{mode === "login" ? "Create an account" : "Sign in"}</button></p></div></div>;
}

function MovementModal({ action, accounts, token, onClose, onComplete }: { action: Exclude<Action, null>; accounts: Account[]; token: string; onClose: () => void; onComplete: () => Promise<void> }) {
  const [account, setAccount] = useState(accounts[0]?.id ?? "");
  const [destination, setDestination] = useState(accounts[1]?.id ?? "");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");
  const submit = async (event: React.FormEvent) => { event.preventDefault(); setError(""); try { const key = `${action}-${crypto.randomUUID()}`; if (action === "deposit") await api.deposit(token, account, amount, key); else if (action === "withdraw") await api.withdraw(token, account, amount, key); else await api.transfer(token, account, destination, amount, key); await onComplete(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Transaction failed"); } };
  return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><div className="modal"><button className="close-button" onClick={onClose}>×</button><div className="modal-icon">{action === "deposit" ? <ArrowDownLeft /> : action === "withdraw" ? <ArrowUpRight /> : <ArrowLeftRight />}</div><p className="eyebrow">SECURE TRANSACTION</p><h2>{action[0].toUpperCase() + action.slice(1)}</h2><p className="form-subtitle">Your request is protected with idempotent processing.</p>{error && <div className="alert error">{error}</div>}<form onSubmit={submit}><label>{action === "transfer" ? "From account" : "Account"}<select value={account} onChange={(e) => setAccount(e.target.value)}>{accounts.map((item) => <option key={item.id} value={item.id}>{item.account_number} · {money(item.available_balance)}</option>)}</select></label>{action === "transfer" && <label>To account<select value={destination} onChange={(e) => setDestination(e.target.value)}>{accounts.filter((item) => item.id !== account).map((item) => <option key={item.id} value={item.id}>{item.account_number}</option>)}</select></label>}<label>Amount<input required type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" /></label><button className="primary-button" type="submit">Confirm {action} <ChevronRight size={17} /></button></form></div></div>;
}

function ActionButton({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) { return <button className="action-button" onClick={onClick}><span>{icon}</span>{label}</button>; }
function SectionTitle({ title, action, onAction }: { title: string; action: string; onAction: () => void }) { return <div className="section-title"><h2>{title}</h2><button onClick={onAction}>{action} <ChevronRight size={14} /></button></div>; }
function ActivityIcon({ type }: { type: string }) { return type === "deposit" ? <ArrowDownLeft size={17} /> : type === "withdrawal" ? <ArrowUpRight size={17} /> : <ArrowLeftRight size={17} />; }
function EmptyState({ text }: { text: string }) { return <div className="empty-state">{text}</div>; }

export default App;
