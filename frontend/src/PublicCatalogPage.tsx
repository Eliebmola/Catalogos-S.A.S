import { useEffect, useState } from "react";
import { Instagram, MessageCircle, Store } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { LoaderCircle } from "lucide-react";

type PublicProduct = { id: string; name: string; description: string | null; price: string; currency: string; image_url: string | null };
type PublicCatalog = { name: string; slug: string; description: string | null; whatsapp_number: string | null; instagram_handle: string | null; brand_image_url: string | null; products: PublicProduct[] };

export function PublicCatalogPage() {
  const { slug = "" } = useParams();
  const [catalog, setCatalog] = useState<PublicCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    fetch(`${(import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "")}/api/v1/public/stores/${encodeURIComponent(slug)}`)
      .then(async response => {
        if (!response.ok) throw new Error("Este catálogo no está disponible.");
        return response.json() as Promise<PublicCatalog>;
      })
      .then(data => { if (active) setCatalog(data); })
      .catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [slug]);

  if (loading) return <main className="public-state"><LoaderCircle className="spin" /></main>;
  if (failed || !catalog) return <main className="public-state"><section><span className="public-brand-mark"><Store size={20} /></span><h1>Catálogo no disponible</h1><p>Revisa el enlace o vuelve a intentarlo más tarde.</p></section></main>;
  const whatsappLink = catalog.whatsapp_number
    ? `https://wa.me/${catalog.whatsapp_number.replace(/\D/g, "")}?text=${encodeURIComponent(`Hola, quiero consultar sobre los productos de ${catalog.name}.`)}`
    : null;

  return <main className="public-page"><style>{`.public-page{min-height:100vh;background:#fafbfc;color:#172033;font-family:"DM Sans",sans-serif}.public-top{height:62px;display:flex;align-items:center;justify-content:space-between;padding:0 max(22px,calc((100% - 1080px)/2));border-bottom:1px solid #e8edf2;background:white;color:#8a94a3;font-size:11px}.public-brand{display:flex;align-items:center;gap:8px;color:#293446;font-weight:700}.public-brand-mark{width:30px;height:30px;display:grid;place-items:center;border-radius:8px;background:#4f46e5;color:white}.public-hero{padding:66px 20px 46px;text-align:center;background:linear-gradient(180deg,#f0efff,#fafbfc)}.public-hero>small{font-size:9px;letter-spacing:.14em;color:#7c75d1;font-weight:700}.public-hero h1{font:800 clamp(28px,5vw,42px) Manrope,sans-serif;letter-spacing:-.045em;margin:12px 0}.public-hero p{max-width:560px;margin:0 auto;color:#7c8796;font-size:13px;line-height:1.7}.public-links{display:flex;justify-content:center;gap:9px;margin-top:22px}.public-products{max-width:1080px;margin:0 auto;padding:28px 20px 70px}.public-products-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:17px}.public-products-title h2{font:700 18px Manrope,sans-serif;margin:0}.public-products-title span{color:#8993a2;font-size:10px}.public-empty{padding:55px 15px;text-align:center;border:1px solid #e9edf2;background:white;border-radius:10px}.public-empty h3{font:700 14px Manrope,sans-serif;margin:0 0 6px}.public-empty p{color:#8a94a3;font-size:11px;margin:0}.public-footer{border-top:1px solid #e9edf2;padding:18px;text-align:center;color:#a0a8b4;font-size:9px}.public-state{min-height:100vh;display:grid;place-items:center;text-align:center;color:#6b7280}.public-state section{padding:30px}.public-state h1{font:700 20px Manrope,sans-serif}.public-state p{font-size:12px}`}</style>
    <header className="public-top"><Link className="public-brand" to="/"><span className="public-brand-mark"><Store size={17} /></span>Catálogos</Link><span>Catálogo digital</span></header>
    <section className="public-hero">{catalog.brand_image_url && <img className="public-brand-logo" src={catalog.brand_image_url} alt={`Logo de ${catalog.name}`} />}<small>CATÁLOGO</small><h1>{catalog.name}</h1>{catalog.description && <p>{catalog.description}</p>}<div className="public-links">{whatsappLink && <a className="primary" href={whatsappLink} target="_blank" rel="noreferrer"><MessageCircle size={16} />Consultar por WhatsApp</a>}{catalog.instagram_handle && <a className="secondary" href={`https://instagram.com/${catalog.instagram_handle}`} target="_blank" rel="noreferrer"><Instagram size={16} />@{catalog.instagram_handle}</a>}</div></section>
    <section className="public-products"><div className="public-products-title"><h2>Productos</h2><span>{catalog.products.length} disponibles</span></div>{catalog.products.length ? <div className="product-grid">{catalog.products.map(product => <article className="product" key={product.id}>{product.image_url ? <img src={product.image_url} alt={product.name} /> : <div className="product-image"><Store size={20} /></div>}<h3>{product.name}</h3><p>{product.description || ""}</p><b>{new Intl.NumberFormat("es-CO", { style: "currency", currency: product.currency }).format(Number(product.price))}</b></article>)}</div> : <div className="public-empty"><h3>Pronto encontrarás productos aquí</h3><p>Este catálogo todavía no tiene productos disponibles.</p></div>}</section>
    <footer className="public-footer">Presentado con Catálogos</footer>
  </main>;
}
