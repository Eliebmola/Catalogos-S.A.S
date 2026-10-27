import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Instagram, LoaderCircle, Minus, MessageCircle, Plus, Printer, Search, ShoppingBag, Store, Trash2, X } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { LanguageSelect, useI18n } from "./i18n";

type PublicProduct = { id: string; name: string; description: string | null; price: string; currency: string; image_url: string | null; category_name: string | null };
type PublicCatalog = { name: string; slug: string; description: string | null; whatsapp_number: string | null; whatsapp_orders_enabled: boolean; instagram_handle: string | null; brand_image_url: string | null; products: PublicProduct[] };
type Buyer = { name: string; phone: string; email: string; requiresShipping: boolean; city: string; neighborhood: string; address: string };
type OrderLine = { product: PublicProduct; quantity: number; lineTotal: number };
type Order = { id: string; createdAt: string; buyer: Buyer; catalog: string; lines: OrderLine[]; totals: Record<string,number>; whatsappUrl: string | null };
const apiUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const emptyBuyer: Buyer = { name: "", phone: "", email: "", requiresShipping: false, city: "", neighborhood: "", address: "" };
const money = (amount: number, currency: string) => new Intl.NumberFormat("es-CO", { style: "currency", currency }).format(amount);

export function PublicCatalogPage() {
  const {t}=useI18n();
  const { slug = "" } = useParams();
  const [catalog, setCatalog] = useState<PublicCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [cartOpen, setCartOpen] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [buyer, setBuyer] = useState<Buyer>(emptyBuyer);
  const [accepted, setAccepted] = useState(false);
  const [order, setOrder] = useState<Order | null>(null);
  const [search, setSearch] = useState("");
  const [orderError, setOrderError] = useState("");
  const [sendingOrder, setSendingOrder] = useState(false);

  useEffect(() => {
    let active = true;
    fetch(`${apiUrl}/api/v1/public/stores/${encodeURIComponent(slug)}`)
      .then(async response => { if (!response.ok) throw new Error(); return response.json() as Promise<PublicCatalog>; })
      .then(data => { if (active) setCatalog(data); })
      .catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [slug]);

  const cartLines = useMemo(() => catalog?.products.flatMap(product => quantities[product.id] ? [{ product, quantity: quantities[product.id] }] : []) || [], [catalog, quantities]);
  const cartCount = cartLines.reduce((total, line) => total + line.quantity, 0);
  const totals = cartLines.reduce<Record<string, number>>((result, line) => {
    result[line.product.currency] = (result[line.product.currency] || 0) + Number(line.product.price) * line.quantity;
    return result;
  }, {});
  const visibleProducts = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("es");
    if (!query) return catalog?.products || [];
    return (catalog?.products || []).filter(product =>
      `${product.name} ${product.description || ""} ${product.category_name || ""}`.toLocaleLowerCase("es").includes(query)
    );
  }, [catalog, search]);
  const groupedProducts = useMemo(() => {
    const groups = new Map<string, PublicProduct[]>();
    for (const product of visibleProducts) {
      const category = product.category_name?.trim() || "Sin categoría";
      groups.set(category, [...(groups.get(category) || []), product]);
    }
    return Array.from(groups, ([name, products]) => ({ name, products }));
  }, [visibleProducts]);

  function changeQuantity(productId: string, amount: number) {
    setQuantities(current => {
      const next = (current[productId] || 0) + amount;
      if (next <= 0) { const { [productId]: _removed, ...rest } = current; return rest; }
      return { ...current, [productId]: Math.min(next, 99) };
    });
  }

  async function createOrder(event: FormEvent) {
    event.preventDefault();
    if (!catalog || cartLines.length === 0) return;
    setSendingOrder(true); setOrderError("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/public/stores/${encodeURIComponent(slug)}/orders`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          buyer_name: buyer.name, buyer_phone: buyer.phone, buyer_email: buyer.email || null,
          requires_shipping: buyer.requiresShipping, city: buyer.requiresShipping ? buyer.city : null,
          neighborhood: buyer.requiresShipping ? buyer.neighborhood : null,
          address: buyer.requiresShipping ? buyer.address : null, privacy_consent: accepted,
          items: cartLines.map(line => ({ product_id: line.product.id, quantity: line.quantity })),
        }),
      });
      const receipt = await response.json().catch(() => null);
      if (!response.ok || !receipt?.saved_for_seller) {
        setOrderError(response.status >= 500
          ? "No pudimos registrar el pedido. Inténtalo de nuevo más tarde."
          : receipt?.error || "No se pudo enviar el pedido. Revisa los datos e inténtalo de nuevo.");
        return;
      }
      const productById = new Map(cartLines.map(line => [line.product.id, line.product]));
      const receiptLines: OrderLine[] = receipt.items.map((item: { product_id: string; name: string; image_url?: string | null; quantity: number; unit_price: string; line_total: string; currency: string }) => ({
        product: { ...productById.get(item.product_id)!, name: item.name, image_url: item.image_url || null, price: item.unit_price, currency: item.currency },
        quantity: item.quantity, lineTotal:Number(item.line_total),
      }));
      setOrder({ id: receipt.id, createdAt: receipt.created_at, buyer: { ...buyer }, catalog: catalog.name, lines: receiptLines, totals:receipt.totals, whatsappUrl: receipt.whatsapp_url || null });
      setCheckoutOpen(false); setCartOpen(false); setAccepted(false);
    } catch {
      setOrderError("No pudimos enviar el pedido. Revisa tu conexión e inténtalo de nuevo.");
    } finally { setSendingOrder(false); }
  }

  if (loading) return <main className="public-state"><LoaderCircle className="spin" /></main>;
  if (failed || !catalog) return <main className="public-state"><section><LanguageSelect/><span className="public-brand-mark"><Store size={20} /></span><h1>{t("storeUnavailable")}</h1><p>{t("checkLink")}</p></section></main>;
  const sellerWhatsapp = catalog.whatsapp_number ? `https://wa.me/${catalog.whatsapp_number.replace(/\D/g, "")}` : null;

  return <main className="public-page shop-page">
    <style>{`.public-page{min-height:100vh;background:#fafbfc;color:#172033;font-family:"DM Sans",sans-serif}.public-top{height:62px;display:flex;align-items:center;justify-content:space-between;padding:0 max(22px,calc((100% - 1080px)/2));border-bottom:1px solid #e8edf2;background:white;color:#8a94a3;font-size:11px}.public-brand{display:flex;align-items:center;gap:8px;color:#293446;font-weight:700}.public-brand-mark{width:30px;height:30px;display:grid;place-items:center;border-radius:8px;background:#4f46e5;color:white}.public-hero{padding:66px 20px 46px;text-align:center;background:linear-gradient(180deg,#f0efff,#fafbfc)}.public-hero>small{font-size:9px;letter-spacing:.14em;color:#7c75d1;font-weight:700}.public-hero h1{font:800 clamp(28px,5vw,42px) Manrope,sans-serif;letter-spacing:-.045em;margin:12px 0}.public-hero p{max-width:560px;margin:0 auto;color:#7c8796;font-size:13px;line-height:1.7}.public-links{display:flex;justify-content:center;gap:9px;margin-top:22px}.public-products{max-width:1080px;margin:0 auto;padding:28px 20px 70px}.public-products-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:17px}.public-products-title h2{font:700 18px Manrope,sans-serif;margin:0}.public-products-title span{color:#8993a2;font-size:10px}.public-empty{padding:55px 15px;text-align:center;border:1px solid #e9edf2;background:white;border-radius:10px}.public-empty h3{font:700 14px Manrope,sans-serif;margin:0 0 6px}.public-empty p{color:#8a94a3;font-size:11px;margin:0}.public-category-section{margin-top:26px}.public-category-heading{display:flex;align-items:center;justify-content:space-between;margin:0 0 12px}.public-category-heading h3{font:700 15px Manrope,sans-serif;margin:0}.public-category-heading span{color:#8993a2;font-size:10px}.public-footer{border-top:1px solid #e9edf2;padding:18px;text-align:center;color:#a0a8b4;font-size:9px}.public-state{min-height:100vh;display:grid;place-items:center;text-align:center;color:#6b7280}.public-state section{padding:30px}.public-state h1{font:700 20px Manrope,sans-serif}.public-state p{font-size:12px}.shop-top-actions{display:flex;align-items:center;gap:13px}`}</style>
    <header className="public-top"><Link className="public-brand" to="/"><span className="public-brand-mark"><Store size={17} /></span>Catálogos</Link><div className="shop-top-actions"><LanguageSelect/><span>{t("catalogDigital")}</span><button className="shop-cart-button" onClick={() => setCartOpen(true)}><ShoppingBag size={16}/>{t("cart")}{cartCount > 0 && <span>{cartCount}</span>}</button></div></header>
    <section className="public-hero">{catalog.brand_image_url && <img className="public-brand-logo" src={catalog.brand_image_url} alt={`${catalog.name}`} />}<small>{t("catalogs").toLocaleUpperCase()}</small><h1>{catalog.name}</h1>{catalog.description && <p>{catalog.description}</p>}<div className="public-links">{sellerWhatsapp && <a className="primary" href={sellerWhatsapp} target="_blank" rel="noreferrer"><MessageCircle size={16}/>{t("askWhatsapp")}</a>}{catalog.instagram_handle && <a className="secondary" href={`https://instagram.com/${catalog.instagram_handle}`} target="_blank" rel="noreferrer"><Instagram size={16}/>@{catalog.instagram_handle}</a>}</div></section>
    <section className="public-products"><div className="public-products-title"><h2>{t("products")}</h2><span>{visibleProducts.length} {t("productsAvailable")}</span></div>{catalog.products.length > 0 && <label className="public-search"><Search size={16}/><input value={search} onChange={event => setSearch(event.target.value)} placeholder={t("searchProducts")} aria-label={t("searchProducts")}/>{search && <button type="button" onClick={() => setSearch("")}>{t("clear")}</button>}</label>}{catalog.products.length === 0 ? <div className="public-empty"><h3>{t("noProducts")}</h3></div> : visibleProducts.length ? <>{groupedProducts.map(group => <section className="public-category-section" key={group.name}><header className="public-category-heading"><h3>{group.name}</h3><span>{group.products.length} {group.products.length === 1 ? "producto" : "productos"}</span></header><div className="product-grid">{group.products.map(product => { const quantity = quantities[product.id] || 0; return <article className="product" key={product.id}>{product.image_url ? <img src={product.image_url} alt={product.name}/> : <div className="product-image"><Store size={20}/></div>}{product.category_name && <small className="public-category-label">{product.category_name}</small>}<h3>{product.name}</h3><p>{product.description || ""}</p><b>{money(Number(product.price), product.currency)}</b>{quantity ? <div className="shop-card-quantity"><button onClick={() => changeQuantity(product.id, -1)} aria-label={`− ${product.name}`}><Minus size={14}/></button><span>{quantity}</span><button onClick={() => changeQuantity(product.id, 1)} aria-label={`+ ${product.name}`}><Plus size={14}/></button></div> : <button className="primary shop-add" onClick={() => changeQuantity(product.id, 1)}><Plus size={15}/>{t("addToCart")}</button>}</article>; })}</div></section>)}</> : <div className="public-empty"><h3>{t("noResults")}</h3><p>{t("noResultsText")}</p></div>}</section>
    <footer className="public-footer">Presentado con Catálogos</footer>

    {cartOpen && <div className="shop-overlay" onMouseDown={event => event.target === event.currentTarget && setCartOpen(false)}><section className="shop-panel" role="dialog" aria-modal="true" aria-label="Carrito de compras"><header><div><h2>Tu carrito</h2><small>{cartCount} {cartCount === 1 ? "producto" : "productos"}</small></div><button className="icon" onClick={() => setCartOpen(false)} aria-label="Cerrar"><X size={18}/></button></header>
      {cartLines.length === 0 ? <div className="shop-empty"><ShoppingBag size={23}/><h3>{t("emptyCart")}</h3><p>{t("addToCart")}</p></div> : <><div className="shop-cart-lines">{cartLines.map(line => <article className="shop-cart-line" key={line.product.id}>{line.product.image_url ? <img src={line.product.image_url} alt=""/> : <span><Store size={16}/></span>}<div className="shop-line-info"><b>{line.product.name}</b><small>{money(Number(line.product.price), line.product.currency)} c/u</small><div className="shop-quantity"><button onClick={() => changeQuantity(line.product.id, -1)} aria-label={`− ${line.product.name}`}><Minus size={13}/></button><span>{line.quantity}</span><button onClick={() => changeQuantity(line.product.id, 1)} aria-label={`+ ${line.product.name}`}><Plus size={13}/></button></div></div><strong>{money(Number(line.product.price) * line.quantity, line.product.currency)}</strong><button className="shop-remove" onClick={() => changeQuantity(line.product.id, -line.quantity)} aria-label={`${t("clear")} ${line.product.name}`}><Trash2 size={15}/></button></article>)}</div><div className="shop-totals">{Object.entries(totals).map(([currency, amount]) => <p key={currency}><span>{t("automaticTotal")} ({currency})</span><b>{money(amount, currency)}</b></p>)}<small>{t("shippingNote")}</small><button className="primary shop-checkout" onClick={() => { setCartOpen(false); setCheckoutOpen(true); }}>{t("continueOrder")}</button></div></>}
    </section></div>}

    {checkoutOpen && <div className="shop-overlay" onMouseDown={event => event.target === event.currentTarget && setCheckoutOpen(false)}><section className="shop-modal" role="dialog" aria-modal="true" aria-label={t("buyerDetails")}><header><div><h2>{t("buyerDetails")}</h2><small>{t("whatsappAfter")}</small></div><button className="icon" onClick={() => setCheckoutOpen(false)} aria-label={t("cancel")}><X size={18}/></button></header><form onSubmit={createOrder}>
      <label>{t("buyerName")}<input required maxLength={120} autoComplete="name" value={buyer.name} onChange={e => setBuyer({...buyer, name:e.target.value})}/></label>
      <label>{t("phone")}<input required type="tel" maxLength={24} autoComplete="tel" value={buyer.phone} onChange={e => setBuyer({...buyer, phone:e.target.value})} placeholder="+57..."/></label>
      <label>{t("emailOptional")}<input type="email" maxLength={160} autoComplete="email" value={buyer.email} onChange={e => setBuyer({...buyer, email:e.target.value})}/></label>
      <label className="shop-check"><input type="checkbox" checked={buyer.requiresShipping} onChange={e => setBuyer({...buyer, requiresShipping:e.target.checked})}/>{t("needsShipping")}</label>
      {buyer.requiresShipping && <div className="shop-address-fields"><label>{t("city")}<input required maxLength={100} autoComplete="address-level2" value={buyer.city} onChange={e => setBuyer({...buyer, city:e.target.value})}/></label><label>{t("neighborhood")}<input required maxLength={100} autoComplete="address-level3" value={buyer.neighborhood} onChange={e => setBuyer({...buyer, neighborhood:e.target.value})}/></label><label>{t("address")}<input required maxLength={180} autoComplete="street-address" value={buyer.address} onChange={e => setBuyer({...buyer, address:e.target.value})}/></label></div>}
      <label className="shop-check shop-consent"><input type="checkbox" required checked={accepted} onChange={e => setAccepted(e.target.checked)}/>Autorizo a Catálogos a registrar estos datos y compartirlos con {catalog.name} únicamente para gestionar este pedido. No se mostrarán en el catálogo público. <Link to="/aviso-de-privacidad">Aviso de privacidad</Link> y <Link to="/terminos">Términos</Link>.</label>
      <div className="shop-order-summary"><b>{t("automaticTotal")}</b>{Object.entries(totals).map(([currency, amount]) => <p key={currency}><span>{t("products")} ({currency})</span><strong>{money(amount, currency)}</strong></p>)}<small>{t("shippingNote")}</small></div>
      <p className="shop-send-note">{t("whatsappAfter")}</p>
      {orderError && <small className="shop-error" role="alert">{orderError}</small>}
      <div className="shop-modal-actions"><button type="button" className="secondary" disabled={sendingOrder} onClick={() => {setCheckoutOpen(false);setCartOpen(true);}}>{t("cart")}</button><button type="submit" className="primary" disabled={sendingOrder}>{sendingOrder ? <LoaderCircle className="spin" size={16}/> : <ShoppingBag size={16}/>} {t("registerOrder")}</button></div>
    </form></section></div>}

    {order && <div className="shop-overlay shop-invoice-overlay"><section className="shop-invoice" role="dialog" aria-modal="true" aria-label="Resumen de pedido"><header className="no-print"><div><small className="eyebrow">PEDIDO {order.id}</small><h2>Resumen de tu pedido</h2></div><button className="icon" onClick={() => setOrder(null)} aria-label="Cerrar"><X size={18}/></button></header><div className="invoice-content"><div className="invoice-brand">{catalog.brand_image_url && <img src={catalog.brand_image_url} alt=""/>}<div><b>{catalog.name}</b><small>Pedido registrado · {new Date(order.createdAt).toLocaleString("es-CO")}</small></div></div><p className="invoice-shipping-note">El pedido quedó guardado en la cuenta del vendedor para que pueda revisar los productos, tus datos y el total.</p><h3>Comprador</h3><p>{order.buyer.name}<br/>{order.buyer.phone}{order.buyer.email && <><br/>{order.buyer.email}</>}</p>{order.buyer.requiresShipping && <><h3>Dirección de envío solicitada</h3><p>{order.buyer.address}<br/>Barrio {order.buyer.neighborhood}<br/>{order.buyer.city}</p></>}<h3>Productos</h3><div className="invoice-lines">{order.lines.map(line => <div key={line.product.id}><span>{line.product.name} × {line.quantity}</span><b>{money(line.lineTotal,line.product.currency)}</b></div>)}</div>{Object.entries(totalsFromOrder(order)).map(([currency, amount])=><div className="invoice-grand-total" key={currency}><span>Total de productos ({currency})</span><b>{money(amount,currency)}</b></div>)}<p className="invoice-shipping-note">El envío no está incluido. El costo y la forma de entrega se acuerdan directamente con el vendedor.</p><p className="invoice-legal-note">Este documento es un resumen de pedido y no constituye una factura electrónica o comprobante de pago.</p></div><div className="shop-invoice-actions no-print">{order.whatsappUrl && <a className="primary" href={order.whatsappUrl} target="_blank" rel="noreferrer"><MessageCircle size={15}/>Abrir WhatsApp para enviar el pedido</a>}<button className="secondary" onClick={() => window.print()}><Printer size={15}/>Guardar o imprimir</button><button className="text-button" onClick={() => {setOrder(null);setQuantities({});}}>Listo</button></div></section></div>}
  </main>;
}

function totalsFromOrder(order: Order) { return order.totals; }
