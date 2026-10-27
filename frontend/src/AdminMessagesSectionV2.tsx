import { useCallback, useEffect, useState, type FormEvent } from "react";
import { LoaderCircle, MessageSquareText, RefreshCw, Send } from "lucide-react";
import { toast } from "sonner";
import { supabase } from "./supabase";

type Category = "catalog_request" | "complaint" | "technical_issue" | "other";
type Status = "new" | "in_progress" | "resolved";
type Reply = { id: string; sender_role: "seller" | "admin"; sender_name: string; body: string; created_at: string };
type Message = { id: string; owner_id: string; seller_name: string | null; seller_email: string | null; business_name: string | null; sender_name: string | null; category: Category; subject: string; body: string; status: Status; sender_role: "seller" | "admin"; replies: Reply[]; created_at: string };
type Account = { owner_id: string; email: string | null; full_name: string | null };
type Recipient = Account & { stores: {id:string;name:string}[] };
const apiBase = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const categoryLabel: Record<Category, string> = { catalog_request: "Solicitud", complaint: "Queja o reclamo", technical_issue: "Problema técnico", other: "Otro" };

async function requestMessages<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  const response = await fetch(`${apiBase}/api/v1/admin/messages${path}`, { ...init, headers });
  if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.error || `No se pudo completar la solicitud (${response.status}).`); }
  return response.json() as Promise<T>;
}

export function AdminMessagesSectionV2({ accounts }: { accounts: Account[] }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [replyText, setReplyText] = useState<Record<string, string>>({});
  const [selectedOwner, setSelectedOwner] = useState("");
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [selectedStore, setSelectedStore] = useState("");
  const [category, setCategory] = useState<Category>("catalog_request");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(async () => {
    try { setMessages(await requestMessages<Message[]>("")); }
    catch (error) { toast.error((error as Error).message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { void requestMessages<Recipient[]>("/recipients").then(setRecipients).catch(error=>toast.error((error as Error).message)); }, []);
  const selectedRecipient=recipients.find(item=>item.owner_id===selectedOwner);

  async function update(message: Message, status: Status) {
    setBusy(message.id);
    try {
      const updated = await requestMessages<Message>(`/${message.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      setMessages(current => current.map(item => item.id === updated.id ? { ...updated, seller_name: item.seller_name, seller_email: item.seller_email } : item));
      toast.success("Estado actualizado.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(null); }
  }

  async function reply(message: Message, event: FormEvent) {
    event.preventDefault();
    const text = replyText[message.id]?.trim();
    if (!text) return;
    setBusy(message.id);
    try {
      await requestMessages<Reply>(`/${message.id}/replies`, { method: "POST", body: JSON.stringify({ body: text }) });
      setReplyText(current => ({ ...current, [message.id]: "" }));
      await refresh();
      toast.success("Respuesta enviada al vendedor.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(null); }
  }

  async function startConversation(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    try {
      await requestMessages<Message>("", { method: "POST", body: JSON.stringify({ owner_id: selectedOwner, store_id:selectedStore||null, category, subject, body }) });
      setSubject(""); setBody("");
      await refresh();
      toast.success("Mensaje enviado al vendedor.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setCreating(false); }
  }

  return <section className="admin-messages-box">
    <style>{`.admin-messages-box{background:white;border:1px solid #e8edf2;border-radius:10px;overflow:hidden}.admin-messages-head{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid #edf0f4}.admin-messages-head h2{display:flex;align-items:center;gap:8px;font:700 14px Manrope,sans-serif;margin:0}.admin-messages-head p{font-size:10px;color:#8590a0;margin:5px 0 0}.admin-messages-head .secondary{min-height:30px;padding:0 9px;font-size:9px}.admin-messages-list{display:grid}.admin-message-row{display:grid;grid-template-columns:minmax(0,1fr) 130px;gap:18px;padding:15px 18px;border-bottom:1px solid #f0f2f5}.admin-message-row:last-child{border-bottom:0}.admin-message-row h3{font:700 11px Manrope,sans-serif;margin:8px 0 4px}.admin-message-row p{font-size:10px;line-height:1.6;color:#626f80;white-space:pre-wrap;margin:8px 0}.admin-message-row small{font-size:9px;color:#8a94a3}.admin-message-meta{display:flex;gap:9px;align-items:center;color:#8a94a3;font-size:9px}.admin-message-category{padding:4px 7px;border-radius:5px;background:#f0efff;color:#5c55b4;font-weight:700}.admin-message-category.complaint{background:#fff0ef;color:#b54137}.admin-message-category.technical_issue{background:#fff4db;color:#996600}.admin-message-controls{display:grid;align-content:start;gap:7px}.admin-message-controls span{font-size:9px;color:#7f8997}.admin-message-controls select{height:32px;border:1px solid #dfe4eb;border-radius:6px;padding:0 7px;font-size:10px;background:white}.admin-messages-empty{padding:32px;text-align:center;color:#8792a1;font-size:11px}.admin-message-loading{padding:22px;text-align:center;color:#7b8493}.admin-start-message{padding:14px 18px;border-bottom:1px solid #edf0f4;background:#fafbfc}.admin-start-message summary{cursor:pointer;color:#5148c8;font-size:10px;font-weight:700}.admin-start-form{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:13px}.admin-start-form label{display:grid;gap:5px;color:#596576;font-size:9px;font-weight:600}.admin-start-form input,.admin-start-form select,.admin-start-form textarea,.admin-reply-form textarea{min-width:0;border:1px solid #dfe4eb;border-radius:6px;background:white;padding:8px;font:10px inherit}.admin-start-form textarea{grid-column:1/-1;min-height:75px;resize:vertical}.admin-start-form button{justify-self:end;grid-column:1/-1;min-height:32px;font-size:9px}.admin-thread{grid-column:1/-1;border:1px solid #edf0f4;border-radius:7px;padding:10px;background:#fafbfc}.admin-thread-item{padding:7px 8px;border-radius:5px;background:white;margin-bottom:6px}.admin-thread-item.admin{background:#f3f2ff}.admin-thread-item small{font-size:8px;color:#8892a1}.admin-thread-item p{margin:4px 0 0}.admin-reply-form{display:flex;gap:7px;margin-top:8px}.admin-reply-form textarea{flex:1;min-height:36px;resize:vertical}.admin-reply-form button{min-height:34px;padding:0 10px;font-size:9px}.admin-priority{font-weight:700;color:#5148c8}@media(max-width:650px){.admin-message-row{grid-template-columns:1fr}.admin-message-controls{grid-template-columns:1fr 1fr;align-items:center}.admin-start-form{grid-template-columns:1fr}.admin-start-form textarea,.admin-start-form button{grid-column:1}}`}</style>
    <header className="admin-messages-head"><div><h2><MessageSquareText size={16}/>Mensajes de vendedores</h2><p>Las solicitudes aparecen primero. Abre una conversación para responder.</p></div><button className="secondary" onClick={() => void refresh()} disabled={loading}><RefreshCw size={14}/>Actualizar</button></header>
    <details className="admin-start-message"><summary>Enviar un mensaje a un vendedor</summary><form className="admin-start-form" onSubmit={startConversation}><label>Vendedor<select required value={selectedOwner} onChange={event => {setSelectedOwner(event.target.value);setSelectedStore("")}}><option value="">Selecciona una cuenta</option>{(recipients.length?recipients:accounts.map(account=>({...account,stores:[]}))).map(account => <option key={account.owner_id} value={account.owner_id}>{account.full_name || "Vendedor"} · {account.email || account.owner_id}</option>)}</select></label><label>Negocio relacionado<select value={selectedStore} disabled={!selectedRecipient?.stores.length} onChange={event=>setSelectedStore(event.target.value)}><option value="">{selectedRecipient?.stores.length?"General / toda la cuenta":"Sin negocios disponibles"}</option>{selectedRecipient?.stores.map(store=><option key={store.id} value={store.id}>{store.name}</option>)}</select></label><label>Categoría<select value={category} onChange={event => setCategory(event.target.value as Category)}><option value="catalog_request">Solicitud</option><option value="complaint">Queja o reclamo</option><option value="technical_issue">Problema técnico</option><option value="other">Otro</option></select></label><label>Asunto<input required minLength={3} maxLength={160} value={subject} onChange={event => setSubject(event.target.value)}/></label><label style={{gridColumn:"1/-1"}}>Mensaje<textarea required minLength={10} maxLength={5000} value={body} onChange={event => setBody(event.target.value)}/></label><button className="primary" disabled={creating || !recipients.length}>{creating ? <LoaderCircle className="spin" size={14}/> : <Send size={14}/>}Enviar al vendedor</button></form></details>
    {loading ? <div className="admin-message-loading"><LoaderCircle className="spin"/></div> : messages.length === 0 ? <div className="admin-messages-empty">Aún no hay conversaciones.</div> : <div className="admin-messages-list">{messages.map(message => <article className="admin-message-row" key={message.id}><div><div className="admin-message-meta"><span className={`admin-message-category ${message.category}`}>{categoryLabel[message.category]}</span>{message.category === "catalog_request" && <span className="admin-priority">Prioridad</span>}<span>{new Date(message.created_at).toLocaleString("es-CO")}</span></div><h3>{message.subject}</h3><small>{message.business_name?`${message.business_name} · `:""}{message.seller_name || "Vendedor"} · {message.seller_email || "Sin correo"}</small><div className="admin-thread"><div className={`admin-thread-item ${message.sender_role}`}><small>{message.sender_role === "admin" ? (message.sender_name||"Administrador") : (message.seller_name || "Vendedor")} · {new Date(message.created_at).toLocaleString("es-CO")}</small><p>{message.body}</p></div>{message.replies.map(item => <div className={`admin-thread-item ${item.sender_role}`} key={item.id}><small>{item.sender_name} · {new Date(item.created_at).toLocaleString("es-CO")}</small><p>{item.body}</p></div>)}<form className="admin-reply-form" onSubmit={event => void reply(message, event)}><textarea aria-label={`Respuesta para ${message.subject}`} required maxLength={5000} placeholder="Escribe una respuesta al vendedor" value={replyText[message.id] || ""} onChange={event => setReplyText(current => ({ ...current, [message.id]: event.target.value }))}/><button className="primary" disabled={busy === message.id}>{busy === message.id ? <LoaderCircle className="spin" size={14}/> : <Send size={14}/>}Responder</button></form></div></div><div className="admin-message-controls"><span>{message.status === "new" ? "Nuevo" : message.status === "in_progress" ? "En revisión" : "Atendido"}</span><select aria-label={`Estado de ${message.subject}`} value={message.status} disabled={busy === message.id} onChange={event => void update(message, event.target.value as Status)}><option value="new">Nuevo</option><option value="in_progress">En revisión</option><option value="resolved">Atendido</option></select></div></article>)}</div>}
  </section>;
}
