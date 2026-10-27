import { type FormEvent, useCallback, useEffect, useState } from "react";
import { LoaderCircle, MessageSquareText, Send } from "lucide-react";
import { toast } from "sonner";
import { supabase } from "./supabase";

type Category = "catalog_request" | "complaint" | "technical_issue" | "other";
type Reply = { id: string; sender_role: "seller" | "admin"; sender_name: string; body: string; created_at: string };
type Store = { id: string; name: string };
type Message = { id: string; category: Category; subject: string; body: string; status: "new" | "in_progress" | "resolved"; sender_role: "seller" | "admin"; sender_name: string | null; seller_name: string | null; business_name: string | null; replies: Reply[]; created_at: string };
const apiBase = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const labels: Record<Category, string> = { catalog_request: "Solicitud", complaint: "Queja o reclamo", technical_issue: "Problema técnico", other: "Otro" };
const statusLabels = { new: "Recibido", in_progress: "En revisión", resolved: "Atendido" };

async function supportRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  const response = await fetch(`${apiBase}/api/v1/support/messages${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.error || "No se pudo completar la solicitud.");
  }
  return response.json() as Promise<T>;
}

export function SupportPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [storeId, setStoreId] = useState("");
  const [category, setCategory] = useState<Category>("catalog_request");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [replyText, setReplyText] = useState<Record<string, string>>({});
  const [replyBusy, setReplyBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try { setMessages(await supportRequest<Message[]>("")); }
    catch (error) { toast.error((error as Error).message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { let active=true; void (async()=>{try{const {data:{session}}=await supabase.auth.getSession();const response=await fetch(`${apiBase}/api/v1/stores`,{headers:session?.access_token?{Authorization:`Bearer ${session.access_token}`}:{}});if(response.ok&&active)setStores(await response.json())}catch{/* El selector es opcional si no hay negocios cargados. */}})();return()=>{active=false}}, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    try {
      const created = await supportRequest<Message>("", { method: "POST", body: JSON.stringify({ category, subject, body, store_id: storeId || null }) });
      setMessages(current => [created, ...current]);
      setSubject(""); setBody("");
      toast.success("Mensaje enviado al equipo administrador.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setSending(false); }
  }

  async function reply(message: Message, event: FormEvent) {
    event.preventDefault();
    const text = replyText[message.id]?.trim();
    if (!text) return;
    setReplyBusy(message.id);
    try {
      await supportRequest<Reply>(`/${message.id}/replies`, { method: "POST", body: JSON.stringify({ body: text }) });
      setReplyText(current => ({ ...current, [message.id]: "" }));
      await refresh();
      toast.success("Respuesta enviada al administrador.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setReplyBusy(null); }
  }

  return <div className="content support-content">
    <style>{`.support-content{max-width:960px}.support-layout{display:grid;grid-template-columns:minmax(280px,.85fr) minmax(0,1.15fr);gap:16px;align-items:start}.support-panel{background:#fff;border:1px solid #e8edf2;border-radius:10px;padding:19px}.support-panel h2{font:700 14px Manrope,sans-serif;margin:0 0 6px}.support-panel>p{color:#8490a0;font-size:10px;line-height:1.6;margin:0 0 16px}.support-form{display:grid;gap:12px}.support-form label{display:grid;gap:6px;font-size:10px;font-weight:600;color:#526071}.support-form input,.support-form select,.support-form textarea{width:100%;border:1px solid #dfe4eb;border-radius:7px;background:white;padding:9px 10px;font:11px inherit;color:#263244}.support-form textarea{resize:vertical;min-height:120px}.support-list{display:grid;gap:9px}.support-message{padding:13px;border:1px solid #edf0f4;border-radius:8px}.support-message header{display:flex;justify-content:space-between;gap:12px}.support-message h3{font:700 11px Manrope,sans-serif;margin:7px 0}.support-message p{white-space:pre-wrap;font-size:10px;line-height:1.6;color:#626f80;margin:0}.support-message small{font-size:9px;color:#8993a2}.support-tag{display:inline-flex;padding:4px 7px;border-radius:5px;background:#f2f1ff;color:#6158b6;font-size:9px;font-weight:700}.support-state{font-size:9px;color:#778293}.support-empty{padding:28px 15px;text-align:center;border:1px dashed #dfe4eb;border-radius:8px;color:#8792a1;font-size:10px}.support-empty svg{color:#837ce0}.support-send{display:flex;justify-content:flex-end}.support-send button{min-height:35px}.support-thread{margin-top:11px;padding:9px;border:1px solid #edf0f4;border-radius:7px;background:#fafbfc}.support-thread-item{padding:8px;border-radius:5px;background:#fff;margin-bottom:6px}.support-thread-item.admin{background:#f3f2ff}.support-thread-item small{font-size:8px;color:#8993a2}.support-thread-item p{margin-top:4px!important}.support-reply{display:flex;gap:7px;margin-top:8px}.support-reply textarea{flex:1;min-height:35px;resize:vertical;border:1px solid #dfe4eb;border-radius:6px;padding:8px;font:10px inherit}.support-reply button{min-height:34px;padding:0 9px;font-size:9px}@media(max-width:760px){.support-layout{grid-template-columns:1fr}}`}</style>
    <div className="heading"><div><small className="eyebrow">AYUDA Y COMUNICACIÓN</small><h1>Mensajes al administrador</h1><p>Envía una solicitud, queja o consulta. Podrás revisar aquí su estado.</p></div></div>
    <div className="support-layout">
      <section className="support-panel"><h2>Nuevo mensaje</h2><p>El equipo administrador recibirá tu mensaje dentro de la aplicación.</p>
        <form className="support-form" onSubmit={submit}>
          <label>Categoría<select value={category} onChange={event => setCategory(event.target.value as Category)}><option value="catalog_request">Solicitud</option><option value="complaint">Queja o reclamo</option><option value="technical_issue">Problema técnico</option><option value="other">Otro</option></select></label>
          {stores.length > 0 && <label>Negocio relacionado<select value={storeId} onChange={event=>setStoreId(event.target.value)}><option value="">General / toda mi cuenta</option>{stores.map(store=><option key={store.id} value={store.id}>{store.name}</option>)}</select></label>}
          <label>Asunto<input required minLength={3} maxLength={160} value={subject} onChange={event => setSubject(event.target.value)} placeholder="Resume el motivo"/></label>
          <label>Mensaje<textarea required minLength={10} maxLength={5000} value={body} onChange={event => setBody(event.target.value)} placeholder="Cuéntanos cómo podemos ayudarte"/></label>
          <div className="support-send"><button className="primary" disabled={sending}>{sending ? <LoaderCircle className="spin" size={15}/> : <Send size={15}/>}Enviar mensaje</button></div>
        </form>
      </section>
      <section className="support-panel"><h2>Conversaciones</h2><p>Consulta el estado y responde a los mensajes del administrador.</p>
        {loading ? <div className="loading-box"><LoaderCircle className="spin"/></div> : messages.length ? <div className="support-list">{messages.map(message => <article className="support-message" key={message.id}><header><span className="support-tag">{labels[message.category]}</span><span className="support-state">{statusLabels[message.status]}</span></header><h3>{message.subject}</h3>{(message.business_name||message.seller_name)&&<small>{message.business_name||"Cuenta"} · {message.seller_name||"Vendedor"}</small>}<div className="support-thread"><div className={`support-thread-item ${message.sender_role}`}><small>{message.sender_role === "admin" ? (message.sender_name||"Administrador") : (message.seller_name||"Tú")} · {new Date(message.created_at).toLocaleString("es-CO")}</small><p>{message.body}</p></div>{message.replies.map(item => <div className={`support-thread-item ${item.sender_role}`} key={item.id}><small>{item.sender_name} · {new Date(item.created_at).toLocaleString("es-CO")}</small><p>{item.body}</p></div>)}<form className="support-reply" onSubmit={event => void reply(message,event)}><textarea required maxLength={5000} placeholder="Escribe una respuesta" value={replyText[message.id]||""} onChange={event=>setReplyText(current=>({...current,[message.id]:event.target.value}))}/><button className="primary" disabled={replyBusy===message.id}>{replyBusy===message.id?<LoaderCircle className="spin" size={14}/>:<Send size={14}/>}Responder</button></form></div></article>)}</div> : <div className="support-empty"><MessageSquareText size={20}/><p>Aún no hay conversaciones.</p></div>}
      </section>
    </div>
  </div>;
}
