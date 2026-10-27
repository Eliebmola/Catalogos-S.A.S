import { useCallback, useEffect, useState } from "react";
import { LoaderCircle, PackageCheck, RefreshCw, ShoppingBag } from "lucide-react";
import { toast } from "sonner";
import { supabase } from "./supabase";

type Status = "new" | "contacted" | "completed" | "cancelled";
type Item = { product_id: string; product_name: string; image_url: string | null; quantity: number; unit_price: string; line_total: string; currency: string };
type Order = { id: string; order_number: string; store_name: string; buyer_name: string; buyer_phone: string; buyer_email: string | null; requires_shipping: boolean; city: string | null; neighborhood: string | null; address: string | null; status: Status; created_at: string; items: Item[]; totals: Record<string, string> };
const apiBase = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const statusLabel: Record<Status, string> = { new: "Nuevo", contacted: "Contactado", completed: "Completado", cancelled: "Cancelado" };
const money = (value: string | number, currency: string) => new Intl.NumberFormat("es-CO", { style: "currency", currency }).format(Number(value));

async function ordersRequest<T>(path = "", init: RequestInit = {}): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  const response = await fetch(`${apiBase}/api/v1/orders${path}`, { ...init, headers });
  if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.error || `No se pudo completar la solicitud (${response.status}).`); }
  return response.json() as Promise<T>;
}

export function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    try { setOrders(await ordersRequest<Order[]>()); }
    catch (error) { toast.error((error as Error).message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  async function update(order: Order, status: Status) {
    setBusy(order.id);
    try {
      const result = await ordersRequest<Order>(`/${order.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      setOrders(current => current.map(item => item.id === result.id ? result : item));
      toast.success("Estado del pedido actualizado.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setBusy(null); }
  }

  return <div className="content seller-orders">
    <style>{`.seller-orders{max-width:1100px}.orders-list{display:grid;gap:11px}.order-card{border:1px solid #e8edf2;border-radius:10px;background:white;overflow:hidden}.order-card-head{display:flex;align-items:center;justify-content:space-between;gap:15px;padding:15px 17px;border-bottom:1px solid #eef1f4}.order-card-title{display:flex;align-items:center;gap:10px}.order-number{font:700 12px Manrope,sans-serif;color:#253044}.order-card-title small{display:block;margin-top:4px;color:#8993a2;font-size:9px}.order-status-select{height:32px;padding:0 8px;border:1px solid #dfe4eb;border-radius:6px;background:white;color:#4b5768;font-size:10px}.order-card-body{display:grid;grid-template-columns:minmax(0,1fr) minmax(230px,.65fr);gap:18px;padding:15px 17px}.order-buyer h3,.order-items h3{font:700 10px Manrope,sans-serif;margin:0 0 8px;color:#596576}.order-buyer p{margin:3px 0;color:#667386;font-size:10px;line-height:1.6}.order-buyer b{color:#243044}.order-items{display:grid;gap:7px}.order-item{display:grid;grid-template-columns:38px minmax(0,1fr) auto;align-items:center;gap:8px;font-size:10px;color:#4c5869}.order-item img,.order-item-placeholder{width:38px;height:38px;object-fit:cover;border-radius:5px;background:#f2f4f7;display:grid;place-items:center;color:#98a1ae}.order-item small{display:block;margin-top:3px;color:#8a94a3;font-size:9px}.order-total{display:grid;gap:4px;padding-top:9px;border-top:1px solid #eef1f4}.order-total p{display:flex;justify-content:space-between;margin:0;font-size:10px;color:#657183}.order-total b{color:#293548}.orders-empty{padding:46px 18px;text-align:center;border:1px solid #e8edf2;border-radius:10px;background:white;color:#8691a0}.orders-empty svg{color:#7169d1}.orders-empty h2{font:700 14px Manrope,sans-serif;color:#344054}.orders-empty p{font-size:10px}@media(max-width:700px){.order-card-body{grid-template-columns:1fr}.order-card-head{align-items:flex-start}.order-card-title{align-items:flex-start}}`}</style>
    <div className="heading"><div><small className="eyebrow">VENTAS</small><h1>Pedidos</h1><p>Revisa lo que cada comprador pidió y actualiza el estado mientras lo atiendes.</p></div><button className="secondary" onClick={() => void refresh()} disabled={loading}><RefreshCw size={14}/>Actualizar</button></div>
    {loading ? <div className="loading-box"><LoaderCircle className="spin"/></div> : orders.length === 0 ? <div className="orders-empty"><ShoppingBag size={23}/><h2>Aún no tienes pedidos</h2><p>Los pedidos que confirmen desde tus catálogos aparecerán aquí con los productos, datos de contacto y total.</p></div> : <div className="orders-list">{orders.map(order => <article className="order-card" key={order.id}><header className="order-card-head"><div className="order-card-title"><PackageCheck size={17}/><div><span className="order-number">Pedido {order.order_number} · {order.store_name}</span><small>{new Date(order.created_at).toLocaleString("es-CO")}</small></div></div><select className="order-status-select" aria-label={`Estado del pedido ${order.order_number}`} value={order.status} disabled={busy===order.id} onChange={event=>void update(order,event.target.value as Status)}>{Object.entries(statusLabel).map(([value,label])=><option value={value} key={value}>{label}</option>)}</select></header><div className="order-card-body"><section className="order-buyer"><h3>Comprador</h3><p><b>{order.buyer_name}</b></p><p>{order.buyer_phone}</p>{order.buyer_email&&<p>{order.buyer_email}</p>}{order.requires_shipping&&<><h3 style={{marginTop:13}}>Dirección solicitada</h3><p>{order.address}<br/>Barrio {order.neighborhood}<br/>{order.city}</p></>}</section><section className="order-items"><h3>Productos solicitados</h3>{order.items.map(item=><div className="order-item" key={item.product_id}>{item.image_url?<img src={item.image_url} alt=""/>:<span className="order-item-placeholder"><ShoppingBag size={15}/></span>}<span>{item.product_name}<small>{item.quantity} × {money(item.unit_price,item.currency)}</small></span><b>{money(item.line_total,item.currency)}</b></div>)}<div className="order-total">{Object.entries(order.totals).map(([currency,total])=><p key={currency}><span>Total de productos ({currency})</span><b>{money(total,currency)}</b></p>)}<small>El costo de envío se acuerda directamente con el comprador.</small></div></section></div></article>)}</div>}
  </div>;
}
