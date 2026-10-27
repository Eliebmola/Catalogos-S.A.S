import { useCallback, useEffect, useState } from "react";
import { LoaderCircle, MessageSquareText, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { supabase } from "./supabase";

type Category = "catalog_request" | "complaint" | "technical_issue" | "other";
type Status = "new" | "in_progress" | "resolved";
type Message = { id: string; owner_id: string; seller_name: string | null; seller_email: string | null; category: Category; subject: string; body: string; status: Status; created_at: string };
const apiBase = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const categoryLabel: Record<Category, string> = { catalog_request: "Solicitud", complaint: "Queja o reclamo", technical_issue: "Problema técnico", other: "Otro" };

async function requestMessages<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  const response = await fetch(`${apiBase}/api/v1/admin/messages${path}`, { ...init, headers });
  if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.error || `Error de API (${response.status})`); }
  return response.json() as Promise<T>;
}

export function AdminMessagesSection() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    try { setMessages(await requestMessages<Message[]>("")); }
    catch (error) { toast.error((error as Error).message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  async function update(message: Message, status: Status) {
    setBusy(message.id);
    try {
      const result = await requestMessages<Message>(`/${message.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      setMessages(current => current.map(item => item.id === result.id ? { ...result, seller_name: item.seller_name, seller_email: item.seller_email } : item));
      toast.success("Estado actualizado.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(null); }
  }

  return <section className="admin-messages-box">
    <style>{`.admin-messages-box{background:white;border:1px solid #e8edf2;border-radius:10px;overflow:hidden}.admin-messages-head{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid #edf0f4}.admin-messages-head h2{display:flex;align-items:center;gap:8px;font:700 14px Manrope,sans-serif;margin:0}.admin-messages-head p{font-size:10px;color:#8590a0;margin:5px 0 0}.admin-messages-head .secondary{min-height:30px;padding:0 9px;font-size:9px}.admin-messages-list{display:grid}.admin-message-row{display:grid;grid-template-columns:minmax(0,1fr) 130px;gap:18px;padding:15px 18px;border-bottom:1px solid #f0f2f5}.admin-message-row:last-child{border-bottom:0}.admin-message-row h3{font:700 11px Manrope,sans-serif;margin:8px 0 4px}.admin-message-row p{font-size:10px;line-height:1.6;color:#626f80;white-space:pre-wrap;margin:8px 0}.admin-message-row small{font-size:9px;color:#8a94a3}.admin-message-meta{display:flex;gap:9px;align-items:center;color:#8a94a3;font-size:9px}.admin-message-category{padding:4px 7px;border-radius:5px;background:#f0efff;color:#5c55b4;font-weight:700}.admin-message-category.complaint{background:#fff0ef;color:#b54137}.admin-message-category.technical_issue{background:#fff4db;color:#996600}.admin-message-controls{display:grid;align-content:center;gap:7px}.admin-message-controls span{font-size:9px;color:#7f8997}.admin-message-controls select{height:32px;border:1px solid #dfe4eb;border-radius:6px;padding:0 7px;font-size:10px;background:white}.admin-messages-empty{padding:32px;text-align:center;color:#8792a1;font-size:11px}.admin-message-loading{padding:22px;text-align:center;color:#7b8493}@media(max-width:650px){.admin-message-row{grid-template-columns:1fr}.admin-message-controls{grid-template-columns:1fr 1fr;align-items:center}}`}</style>
    <header className="admin-messages-head"><div><h2><MessageSquareText size={16}/>Mensajes de vendedores</h2><p>Las solicitudes aparecen primero. Al abrir esta bandeja, los mensajes nuevos se marcan como vistos.</p></div><button className="secondary" onClick={() => void refresh()} disabled={loading}><RefreshCw size={14}/>Actualizar</button></header>
    {loading ? <div className="admin-message-loading"><LoaderCircle className="spin"/></div> : messages.length === 0 ? <div className="admin-messages-empty">Aún no has recibido mensajes de vendedores.</div> : <div className="admin-messages-list">{messages.map(message => <article className="admin-message-row" key={message.id}><div><div className="admin-message-meta"><span className={`admin-message-category ${message.category}`}>{categoryLabel[message.category]}</span><span>{new Date(message.created_at).toLocaleString("es-CO")}</span></div><h3>{message.subject}</h3><small>{message.seller_name || "Vendedor"} · {message.seller_email || "Sin correo"}</small><p>{message.body}</p></div><div className="admin-message-controls"><span>{message.status === "new" ? "Nuevo" : message.status === "in_progress" ? "En revisión" : "Atendido"}</span><select aria-label={`Estado de ${message.subject}`} value={message.status} disabled={busy === message.id} onChange={event => void update(message, event.target.value as Status)}><option value="new">Nuevo</option><option value="in_progress">En revisión</option><option value="resolved">Atendido</option></select></div></article>)}</div>}
  </section>;
}
