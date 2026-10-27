import { useCallback, useEffect, useState } from "react";
import { LoaderCircle, RefreshCw, Save, Shield, WalletCards } from "lucide-react";
import { toast } from "sonner";
import { supabase } from "./supabase";
import { AdminMessagesSectionV2 } from "./AdminMessagesSectionV2";

type Account = {
  owner_id: string; email: string | null; full_name: string | null; catalog_count: number;
  whatsapp_number: string | null; paid_through: string | null; trial_until: string | null; extra_catalogs: number; status: string;
  access_override: boolean | null; legacy_grandfathered: boolean;
};
type ProviderStatus = { grace_days: number; trial_days:number; monthly_price_cop:number; extra_catalog_price_cop:number; max_image_bytes: number; email_notifications_ready: boolean; whatsapp_notifications_ready: boolean; whatsapp_orders_ready: boolean };
const baseUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function adminRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  const response = await fetch(`${baseUrl}/api/v1/admin/subscriptions${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.error || `Error de API (${response.status})`);
  }
  return response.json() as Promise<T>;
}

const statusLabel: Record<string, string> = {
  active: "Al día", trial: "Prueba gratuita", grace: "En periodo de gracia", suspended: "Suspendida",
  blocked: "Bloqueo manual", pending_payment: "Pendiente de pago",
  manual_access: "Acceso manual", legacy: "Cuenta existente por configurar",
};

export function AdminPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [providers, setProviders] = useState<ProviderStatus | null>(null);
  const [phones, setPhones] = useState<Record<string, string>>({});
  const [extraCatalogs, setExtraCatalogs] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [denied, setDenied] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [rows, status] = await Promise.all([
        adminRequest<Account[]>(""), adminRequest<ProviderStatus>("/notification-status"),
      ]);
      setAccounts(rows);
      setProviders(status);
      setPhones(Object.fromEntries(rows.map(row => [row.owner_id, row.whatsapp_number || ""])));
      setExtraCatalogs(Object.fromEntries(rows.map(row => [row.owner_id, row.extra_catalogs || 0])));
      setDenied(false);
    } catch (error) {
      const message = (error as Error).message;
      if (/permisos|administrador/i.test(message)) setDenied(true);
      else toast.error(message);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  async function mutate(ownerId: string, path: string, body: unknown, success: string) {
    setBusy(ownerId);
    try {
      const updated = await adminRequest<Account>(`/${ownerId}/${path}`, { method: path === "payments" ? "POST" : "PATCH", body: JSON.stringify(body) });
      setAccounts(current => current.map(row => row.owner_id === ownerId ? updated : row));
      if (updated.whatsapp_number !== undefined) setPhones(current => ({ ...current, [ownerId]: updated.whatsapp_number || "" }));
      toast.success(success);
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(null); }
  }

  if (denied) return <div className="content"><section className="panel admin-denied"><Shield size={25}/><h1>Acceso restringido</h1><p>Esta sección es solo para administradores autorizados.</p></section></div>;

  return <div className="content admin-content">
    <style>{`.admin-content .heading{align-items:center}.admin-intro{max-width:650px}.admin-note{padding:13px 15px;border:1px solid #e5e7eb;border-radius:8px;background:#fff;font-size:10px;color:#647084;line-height:1.6}.admin-note b{color:#344054}.admin-grid{display:grid;gap:10px}.admin-account{display:grid;grid-template-columns:minmax(150px,1.1fr) minmax(150px,1fr) minmax(150px,.8fr) minmax(170px,.9fr) minmax(245px,1.25fr);align-items:center;gap:13px;padding:15px;background:white;border:1px solid #e8edf2;border-radius:9px}.admin-person b,.admin-person small,.admin-subscription b,.admin-subscription small{display:block}.admin-person b,.admin-subscription b{font-size:11px}.admin-person small,.admin-subscription small{margin-top:4px;font-size:9px;color:#8a94a3}.admin-phone,.admin-extra{display:flex;gap:6px;min-width:0}.admin-phone input,.admin-extra input{min-width:0;width:100%;height:36px;padding:0 8px;border:1px solid #dfe4eb;border-radius:6px;font-size:10px}.admin-extra input{width:74px}.admin-extra button{min-height:36px;padding:0 9px}.admin-extra label{display:grid;gap:4px;color:#697586;font-size:9px}.admin-actions{display:flex;justify-content:flex-end;flex-wrap:wrap;gap:6px}.admin-actions button,.admin-phone button{min-height:36px;padding:0 9px;font-size:9px}.admin-status{display:inline-flex;width:fit-content;margin-top:6px;padding:4px 7px;border-radius:5px;background:#f0f2f5;color:#657082;font-size:9px;font-weight:600}.admin-status.active,.admin-status.manual_access,.admin-status.legacy,.admin-status.trial{background:#e9f8f0;color:#138154}.admin-status.grace{background:#fff4db;color:#996600}.admin-status.suspended,.admin-status.blocked,.admin-status.pending_payment{background:#fff0ef;color:#b54137}.admin-empty{padding:35px;text-align:center;color:#8590a0;font-size:12px;background:white;border:1px solid #e8edf2;border-radius:9px}.admin-denied{text-align:center;padding:55px 20px}.admin-denied svg{color:#695fc9}.admin-denied h1{font:700 19px Manrope,sans-serif}.admin-denied p{font-size:11px;color:#8791a0}@media(max-width:1150px){.admin-account{grid-template-columns:1fr 1fr}.admin-actions{justify-content:flex-start}}@media(max-width:600px){.admin-account{grid-template-columns:1fr;gap:12px}.admin-phone{max-width:100%}.admin-extra{max-width:100%}.admin-actions{display:grid;grid-template-columns:1fr 1fr}}`}</style>
    <div className="heading"><div className="admin-intro"><small className="eyebrow">ADMINISTRACIÓN</small><h1>Administración</h1><p>Gestiona cuentas, renovaciones y mensajes recibidos de los vendedores.</p></div><button className="secondary" onClick={() => void refresh()} disabled={loading}><RefreshCw size={15}/>Actualizar</button></div>
    <AdminMessagesSectionV2 accounts={accounts} />
    {providers && <div className="admin-note"><b>Prueba:</b> {providers.trial_days} días. <b>Gracia:</b> {providers.grace_days} días. <b>Plan:</b> {providers.monthly_price_cop.toLocaleString("es-CO")} COP/mes con 2 catálogos; <b>extra:</b> {providers.extra_catalog_price_cop.toLocaleString("es-CO")} COP por catálogo/mes. <b>Imágenes:</b> hasta {(providers.max_image_bytes / 1024 / 1024).toFixed(0)} MiB. <b>Avisos email:</b> {providers.email_notifications_ready ? "configurados" : "pendientes de proveedor"}. <b>Avisos WhatsApp:</b> {providers.whatsapp_notifications_ready ? "configurados" : "pendientes de proveedor"}.</div>}
    {loading ? <div className="loading-box"><LoaderCircle className="spin"/></div> : accounts.length === 0 ? <div className="admin-empty">Aún no hay cuentas registradas en el panel.</div> : <div className="admin-grid">
      {accounts.map(account => {
        const isBlocked = ["blocked", "pending_payment", "suspended"].includes(account.status);
        return <article className="admin-account" key={account.owner_id}>
          <div className="admin-person"><b>{account.full_name || "Vendedor"}</b><small>{account.email || "Sin correo asociado"}</small></div>
          <div className="admin-subscription"><b>{account.catalog_count} catálogo(s) · límite {2 + account.extra_catalogs}</b><span className={`admin-status ${account.status}`}>{statusLabel[account.status] || account.status}</span><small>{account.paid_through ? `Vence: ${new Date(`${account.paid_through}T12:00:00`).toLocaleDateString("es-CO")}` : account.trial_until ? `Prueba hasta: ${new Date(`${account.trial_until}T12:00:00`).toLocaleDateString("es-CO")}` : "Sin fecha de pago registrada"}</small>{providers&&<small>Mensualidad estimada: {(providers.monthly_price_cop+account.extra_catalogs*providers.extra_catalog_price_cop).toLocaleString("es-CO")} COP</small>}</div>
          <div className="admin-phone"><input aria-label={`WhatsApp de ${account.email || "la cuenta"}`} type="tel" placeholder="+573001234567" value={phones[account.owner_id] || ""} onChange={event => setPhones(current => ({ ...current, [account.owner_id]: event.target.value }))}/><button className="secondary" title="Guardar WhatsApp" disabled={busy === account.owner_id} onClick={() => void mutate(account.owner_id, "contact", { whatsapp_number: phones[account.owner_id]?.trim() || null }, "WhatsApp de avisos guardado.")}><Save size={14}/></button></div>
          <div className="admin-extra"><label>Catálogos extra permitidos<input aria-label={`Catálogos extra permitidos para ${account.email||"la cuenta"}`} type="number" min="0" max="100" value={extraCatalogs[account.owner_id]??0} onChange={event=>setExtraCatalogs(current=>({...current,[account.owner_id]:Math.max(0,Number(event.target.value))}))}/></label><button className="secondary" disabled={busy===account.owner_id} onClick={()=>void mutate(account.owner_id,"extra-catalogs",{extra_catalogs:extraCatalogs[account.owner_id]??0},"Límite de catálogos actualizado.")}><Save size={14}/></button></div>
          <div className="admin-actions"><button className="primary" disabled={busy === account.owner_id} onClick={() => void mutate(account.owner_id, "payments", {}, "Pago registrado; acceso renovado por un mes.")}><WalletCards size={14}/>Registrar pago</button><button className={isBlocked ? "primary" : "secondary"} disabled={busy === account.owner_id} onClick={() => void mutate(account.owner_id, "access", { blocked: !isBlocked }, isBlocked ? "Acceso habilitado manualmente." : "Catálogos bloqueados.")}>{isBlocked ? "Desbloquear" : "Bloquear"}</button>{account.access_override !== null && <button className="secondary" disabled={busy === account.owner_id} onClick={() => void mutate(account.owner_id, "access", { blocked: null }, "Acceso vuelve al control automático.")}>Control automático</button>}</div>
        </article>;
      })}
    </div>}
  </div>;
}
