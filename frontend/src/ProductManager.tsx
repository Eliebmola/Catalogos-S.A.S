import { useEffect, useState, type FormEvent } from "react";
import { AlertTriangle, ArrowLeft, Copy, ExternalLink, ImagePlus, LoaderCircle, Pencil, Plus, Share2, Store, Trash2, X, Camera, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Link, useNavigate } from "react-router-dom";
import { supabase } from "./supabase";

type Catalog = { id: string; name: string; slug: string; description: string | null; whatsapp_number: string | null; whatsapp_orders_opt_in: boolean; instagram_handle: string | null; brand_image_url: string | null; is_published: boolean };
type Product = { id: string; store_id: string; category_id: string | null; name: string; description: string | null; price: string; currency: string; image_url: string | null; is_active: boolean; sort_order: number };
type Category = { id: string; store_id: string; name: string; created_at: string; updated_at: string };
const apiUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const maxImageBytes = 2 * 1024 * 1024;

async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  const response = await fetch(`${apiUrl}/api/v1${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.error || "No se pudo completar la solicitud. Inténtalo de nuevo.");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function sendImage(storeId: string, productId: string, file: File): Promise<Product> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers();
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  const form = new FormData();
  form.append("file", file);
  let response: Response;
  try {
    response = await fetch(`${apiUrl}/api/v1/stores/${storeId}/products/${productId}/image`, { method: "POST", headers, body: form });
  } catch {
    throw new Error("No se pudo subir la imagen. Estamos revisando el servicio para solucionarlo pronto.");
  }
  if (!response.ok) {
    if (response.status >= 500) throw new Error("No se pudo subir la imagen. Estamos revisando el servicio para solucionarlo pronto.");
    const body = await response.json().catch(() => null);
    throw new Error(body?.error || "No se pudo subir la imagen. Revisa el archivo e inténtalo de nuevo.");
  }
  return response.json() as Promise<Product>;
}

function formatPrice(price: string, currency: string) {
  return new Intl.NumberFormat("es-CO", { style: "currency", currency }).format(Number(price));
}

export function ProductManager({ storeId }: { storeId: string }) {
  const navigate = useNavigate();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [editor, setEditor] = useState<Product | null | undefined>(undefined);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [active, setActive] = useState(true);
  const [image, setImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [brandName, setBrandName] = useState("");
  const [brandDescription, setBrandDescription] = useState("");
  const [brandWhatsapp, setBrandWhatsapp] = useState("");
  const [brandInstagram, setBrandInstagram] = useState("");
  const [brandImage, setBrandImage] = useState<File | null>(null);
  const [removeBrandImage, setRemoveBrandImage] = useState(false);
  const [brandPreview, setBrandPreview] = useState<string | null>(null);
  const [categoryModal, setCategoryModal] = useState(false);
  const [categoryName, setCategoryName] = useState("");
  const [categorySaving, setCategorySaving] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState("");
  const [whatsappOrdersEnabled, setWhatsappOrdersEnabled] = useState(false);
  const [whatsappWarningOpen, setWhatsappWarningOpen] = useState(false);
  const [whatsappDisclosureAccepted, setWhatsappDisclosureAccepted] = useState(false);
  const [deleteStage, setDeleteStage] = useState<"warning" | "confirm" | null>(null);
  const [deleteName, setDeleteName] = useState("");
  const [deletingCatalog, setDeletingCatalog] = useState(false);

  async function refreshProducts() {
    const rows = await apiRequest<Product[]>(`/stores/${storeId}/products`);
    setProducts(rows);
  }

  async function refreshCategories() {
    setCategories(await apiRequest<Category[]>(`/stores/${storeId}/categories`));
  }

  async function assignCategory(product: Product, categoryId: string) {
    try {
      const updated = await apiRequest<Product>(`/stores/${storeId}/products/${product.id}`, {
        method: "PATCH", body: JSON.stringify({ category_id: categoryId || null }),
      });
      setProducts(current => current.map(item => item.id === updated.id ? updated : item));
      toast.success(categoryId ? "Categoría asignada." : "Producto sin categoría.");
    } catch (error) { toast.error((error as Error).message); }
  }

  async function createCategory(event: FormEvent) {
    event.preventDefault(); setCategorySaving(true);
    try {
      const created = await apiRequest<Category>(`/stores/${storeId}/categories`, {
        method: "POST", body: JSON.stringify({ name: categoryName.trim() }),
      });
      setCategories(current => [...current, created].sort((a,b) => a.name.localeCompare(b.name, "es")));
      setCategoryName(""); toast.success("Categoría creada.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setCategorySaving(false); }
  }

  async function renameCategory(category: Category) {
    const value = window.prompt("Nuevo nombre de la categoría", category.name)?.trim();
    if (!value || value === category.name) return;
    try {
      const updated = await apiRequest<Category>(`/stores/${storeId}/categories/${category.id}`, {
        method: "PATCH", body: JSON.stringify({ name: value }),
      });
      setCategories(current => current.map(item => item.id === updated.id ? updated : item).sort((a,b) => a.name.localeCompare(b.name, "es")));
      toast.success("Categoría actualizada.");
    } catch (error) { toast.error((error as Error).message); }
  }

  async function deleteCategory(category: Category) {
    if (!window.confirm(`¿Eliminar la categoría “${category.name}”? Sus productos quedarán sin categoría.`)) return;
    try {
      await apiRequest<void>(`/stores/${storeId}/categories/${category.id}`, { method: "DELETE" });
      setCategories(current => current.filter(item => item.id !== category.id));
      await refreshProducts(); toast.success("Categoría eliminada.");
    } catch (error) { toast.error((error as Error).message); }
  }

  async function setPublication(isPublished: boolean) {
    if (!catalog) return;
    setPublishing(true);
    try {
      const updated = await apiRequest<Catalog>(`/stores/${storeId}/publication`, {
        method: "PATCH", body: JSON.stringify({ is_published: isPublished }),
      });
      setCatalog(updated);
      toast.success(isPublished ? "Catálogo publicado. Ya puedes compartir el enlace." : "Catálogo guardado como borrador.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setPublishing(false); }
  }

  async function copyCatalogLink() {
    if (!catalog) return;
    const publicUrl = `${window.location.origin}/c/${catalog.slug}`;
    try {
      await navigator.clipboard.writeText(publicUrl);
      toast.success("Enlace copiado. Ya puedes pegarlo en tu perfil o enviarlo a tus clientes.");
    } catch { toast.error("No se pudo copiar el enlace. Inténtalo de nuevo."); }
  }

  async function shareCatalogLink() {
    if (!catalog) return;
    const publicUrl = `${window.location.origin}/c/${catalog.slug}`;
    if (navigator.share) {
      try { await navigator.share({ title: catalog.name, text: `Mira mi catálogo: ${catalog.name}`, url: publicUrl }); }
      catch (error) { if ((error as Error).name !== "AbortError") await copyCatalogLink(); }
    } else await copyCatalogLink();
  }

  useEffect(() => {
    let current = true;
    async function load() {
      setLoading(true);
      try {
        const catalogs = await apiRequest<Catalog[]>("/stores");
        const found = catalogs.find(item => item.id === storeId);
        if (!found) throw new Error("No se encontró este catálogo.");
        const [rows, categoryRows] = await Promise.all([
          apiRequest<Product[]>(`/stores/${storeId}/products`),
          apiRequest<Category[]>(`/stores/${storeId}/categories`),
        ]);
        if (current) { setCatalog(found); setProducts(rows); setCategories(categoryRows); }
      } catch (error) {
        if (current) toast.error((error as Error).message);
      } finally { if (current) setLoading(false); }
    }
    void load();
    return () => { current = false; };
  }, [storeId]);

  useEffect(() => {
    if (!image) { setPreviewUrl(editor?.image_url || null); return; }
    const url = URL.createObjectURL(image);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [image, editor]);

  useEffect(() => {
    if (!brandImage) { setBrandPreview(removeBrandImage ? null : catalog?.brand_image_url || null); return; }
    const url = URL.createObjectURL(brandImage);
    setBrandPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [brandImage, removeBrandImage, catalog]);

  function openProfile() {
    if (!catalog) return;
    setBrandName(catalog.name); setBrandDescription(catalog.description || "");
    setBrandWhatsapp(catalog.whatsapp_number || ""); setBrandInstagram(catalog.instagram_handle || "");
    setWhatsappOrdersEnabled(catalog.whatsapp_orders_opt_in);
    setWhatsappDisclosureAccepted(false); setWhatsappWarningOpen(false);
    setBrandImage(null); setRemoveBrandImage(false); setProfileOpen(true);
  }

  async function saveProfile(event: FormEvent) {
    event.preventDefault(); setProfileSaving(true);
    try {
      let updated = await apiRequest<Catalog>(`/stores/${storeId}`, { method: "PATCH", body: JSON.stringify({
        name: brandName.trim(), description: brandDescription.trim() || null,
        whatsapp_number: brandWhatsapp.trim() || null, instagram_handle: brandInstagram.trim().replace(/^@/, "") || null,
        whatsapp_orders_opt_in: whatsappOrdersEnabled,
      }) });
      if (brandImage) {
        const { data: { session } } = await supabase.auth.getSession();
        const headers = new Headers(); if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
        const form = new FormData(); form.append("file", brandImage);
        const response = await fetch(`${apiUrl}/api/v1/stores/${storeId}/brand-image`, { method: "POST", headers, body: form });
        if (!response.ok) throw new Error(response.status >= 500 ? "No se pudo subir el logo. Estamos revisando el servicio para solucionarlo pronto." : (await response.json().catch(() => null))?.error || "No se pudo subir el logo. Revisa el archivo e inténtalo de nuevo.");
        updated = await response.json() as Catalog;
      } else if (removeBrandImage && catalog?.brand_image_url) {
        updated = await apiRequest<Catalog>(`/stores/${storeId}/brand-image`, { method: "DELETE" });
      }
      setCatalog(updated); setProfileOpen(false); toast.success("Perfil de marca actualizado.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setProfileSaving(false); }
  }

  function chooseBrandImage(file: File | null) {
    if (file && file.size > maxImageBytes) { toast.error("El logo no puede superar 2 MiB."); return; }
    if (file && !["image/jpeg", "image/png", "image/webp"].includes(file.type)) { toast.error("Elige una imagen JPEG, PNG o WebP."); return; }
    setBrandImage(file); setRemoveBrandImage(false);
  }

  function openNew() {
    setEditor(null); setName(""); setDescription(""); setPrice(""); setActive(true); setImage(null); setSelectedCategoryId("");
  }

  function openEdit(product: Product) {
    setEditor(product); setName(product.name); setDescription(product.description || ""); setPrice(product.price); setActive(product.is_active); setImage(null); setSelectedCategoryId(product.category_id || "");
  }

  function chooseImage(file: File | null) {
    if (file && file.size > maxImageBytes) { toast.error("La imagen no puede superar 2 MiB."); return; }
    if (file && !["image/jpeg", "image/png", "image/webp"].includes(file.type)) { toast.error("Elige una imagen JPEG, PNG o WebP."); return; }
    setImage(file);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = { name: name.trim(), description: description.trim() || null, price, is_active: active, category_id: selectedCategoryId || null };
      let saved: Product;
      if (editor) {
        saved = await apiRequest<Product>(`/stores/${storeId}/products/${editor.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      } else {
        saved = await apiRequest<Product>(`/stores/${storeId}/products`, { method: "POST", body: JSON.stringify({ ...payload, currency: "COP", sort_order: products.length }) });
      }
      let imageFailed = false;
      if (image) {
        try { saved = await sendImage(storeId, saved.id, image); }
        catch { imageFailed = true; }
      }
      await refreshProducts();
      setEditor(undefined); setImage(null);
      if (imageFailed) toast.error("El producto se guardó, pero no pudimos subir la imagen. Estamos revisando el servicio para solucionarlo pronto.");
      else toast.success(editor ? "Cambios guardados." : "Producto creado.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setSaving(false); }
  }

  async function removeImage(product: Product) {
    setSaving(true);
    try {
      const updated = await apiRequest<Product>(`/stores/${storeId}/products/${product.id}/image`, { method: "DELETE" });
      setProducts(current => current.map(item => item.id === updated.id ? updated : item));
      setEditor(updated); setImage(null);
      toast.success("Imagen quitada.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setSaving(false); }
  }

  async function deleteProduct(product: Product) {
    if (!window.confirm(`¿Eliminar “${product.name}” y su imagen?`)) return;
    setSaving(true);
    try {
      await apiRequest<void>(`/stores/${storeId}/products/${product.id}`, { method: "DELETE" });
      setProducts(current => current.filter(item => item.id !== product.id));
      toast.success("Producto eliminado.");
    } catch (error) { toast.error((error as Error).message); }
    finally { setSaving(false); }
  }

  async function permanentlyDeleteCatalog() {
    if (!catalog || deleteName.trim() !== catalog.name) return;
    setDeletingCatalog(true);
    try {
      await apiRequest<void>(`/stores/${storeId}`, {
        method: "DELETE", body: JSON.stringify({ confirmation_name: deleteName.trim() }),
      });
      toast.success("El catálogo y sus productos se eliminaron permanentemente.");
      navigate("/catalogos", { replace: true });
    } catch (error) { toast.error((error as Error).message); }
    finally { setDeletingCatalog(false); }
  }

  if (loading) return <div className="content"><div className="loading-box"><LoaderCircle className="spin"/></div></div>;
  if (!catalog) return <div className="content"><div className="product-manager-back"><button className="text-button" onClick={() => navigate("/catalogos")}><ArrowLeft size={15}/>Volver a catálogos</button></div><section className="panel"><h2>Catálogo no disponible</h2><p>Vuelve al listado de catálogos e inténtalo de nuevo.</p></section></div>;

  return <div className="content">
    <Link className="back" to="/catalogos"><ArrowLeft size={14}/> Todos los catálogos</Link>
    <div className="heading product-manager-heading"><div className="brand-heading">{catalog.brand_image_url ? <img className="brand-avatar" src={catalog.brand_image_url} alt="Logo de la marca"/> : <span className="brand-avatar brand-avatar-empty"><Store size={19}/></span>}<div><small className="eyebrow">CATÁLOGO</small><h1>{catalog.name}</h1><p>{catalog.description || "Administra los productos de este catálogo."}</p></div></div><div className="product-manager-actions"><button className="secondary" onClick={openProfile}><Pencil size={15}/>Editar perfil</button><button className="primary" onClick={openNew}><Plus size={16}/>Agregar producto</button><button className="catalog-delete-trigger" onClick={() => {setDeleteName("");setDeleteStage("warning");}}><Trash2 size={15}/>Eliminar catálogo</button></div></div>
    <section className="catalog-share-panel"><div className="catalog-share-info"><small className="eyebrow">ENLACE PARA TUS CLIENTES</small><code>{window.location.origin}/c/{catalog.slug}</code><p>{catalog.is_published ? "Este enlace abre tu catálogo público sin que tus clientes tengan que iniciar sesión." : "Publica el catálogo para que tus clientes puedan abrir este enlace."}</p></div><div className="catalog-share-actions">{catalog.is_published ? <><a className="secondary" href={`/c/${catalog.slug}`} target="_blank" rel="noreferrer"><ExternalLink size={15}/>Vista previa</a><button className="secondary" onClick={() => void copyCatalogLink()}><Copy size={15}/>Copiar enlace</button><button className="primary" onClick={() => void shareCatalogLink()}><Share2 size={15}/>Compartir</button></> : <button className="primary" disabled={publishing} onClick={() => void setPublication(true)}>{publishing ? <LoaderCircle className="spin" size={15}/> : <ExternalLink size={15}/>}Publicar catálogo</button>}{catalog.is_published && <button className="catalog-unpublish" disabled={publishing} onClick={() => void setPublication(false)}>Dejar como borrador</button>}</div></section>
    <section className="panel"><div className="section-title"><div><h2>Productos</h2><p>{products.length} {products.length === 1 ? "producto" : "productos"} en este catálogo.</p></div><button className="secondary" onClick={() => setCategoryModal(true)}><Store size={14}/>Categorías{categories.length ? ` (${categories.length})` : ""}</button></div>
      {products.length === 0 ? <div className="empty"><span className="empty-mark"><Store size={20}/></span><h3>Aún no hay productos</h3><p>Agrega productos para mostrarlos a tus clientes.</p></div> : <div className="product-grid">{products.map(product => <article className="product seller-product" key={product.id}>
        {product.image_url ? <img src={product.image_url} alt={product.name}/> : <div className="product-image"><ImagePlus size={22}/></div>}
        <div className="seller-product-body"><h3>{product.name}</h3><p>{product.description || "Sin descripción."}</p><b>{formatPrice(product.price, product.currency)}</b>{!product.is_active && <small className="inactive-product">Oculto del catálogo público</small>}
          <div className="seller-product-actions"><select aria-label={`Categoría de ${product.name}`} value={product.category_id || ""} onChange={event => void assignCategory(product, event.target.value)}><option value="">Sin categoría</option>{categories.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}</select><button className="secondary" disabled={saving} onClick={() => openEdit(product)}><Pencil size={14}/>Editar</button><button className="danger-quiet" disabled={saving} aria-label={`Eliminar ${product.name}`} title="Eliminar producto" onClick={() => void deleteProduct(product)}><Trash2 size={15}/></button></div>
        </div>
      </article>)}</div>}
    </section>

    {editor !== undefined && <div className="overlay" onMouseDown={event => event.target === event.currentTarget && setEditor(undefined)}><section className="modal product-editor-modal"><header><div><h2>{editor ? "Editar producto" : "Agregar producto"}</h2><small>Así se mostrará en el catálogo de tus clientes</small></div><button className="icon" onClick={() => setEditor(undefined)} aria-label="Cerrar"><X size={18}/></button></header>
      <form className="product-editor-form" onSubmit={save}>
        <div className="product-editor-fields">
          <label>Nombre<input required minLength={2} maxLength={150} value={name} onChange={event => setName(event.target.value)} placeholder="Ej. Camisa de lino"/></label>
          <label>Descripción <em>Opcional</em><textarea rows={3} maxLength={2000} value={description} onChange={event => setDescription(event.target.value)} placeholder="Describe el producto para tus clientes."/></label>
          <label>Categoría <em>Opcional</em><select value={selectedCategoryId} onChange={event => setSelectedCategoryId(event.target.value)}><option value="">Sin categoría</option>{categories.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
          <label>Precio (COP)<input required type="number" min="0" step="0.01" value={price} onChange={event => setPrice(event.target.value)} placeholder="0"/></label>
          <label className="product-image-field">Imagen <em>Opcional · JPEG, PNG o WebP · máximo 2 MiB</em><input type="file" accept="image/jpeg,image/png,image/webp" onChange={event => chooseImage(event.target.files?.[0] || null)}/>{image && <small>{image.name}</small>}</label>
          <label className="product-active-choice"><input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)}/>Mostrar en el catálogo público</label>
          {editor?.image_url && !image && <button type="button" className="remove-image-link" disabled={saving} onClick={() => void removeImage(editor)}>Quitar imagen actual</button>}
        </div>
        <aside className="product-live-preview"><small className="eyebrow">VISTA PREVIA</small><article className="public-product-preview">{previewUrl ? <img src={previewUrl} alt="Vista previa de la imagen del producto"/> : <div className="product-image"><ImagePlus size={22}/></div>}<div><h3>{name || "Nombre del producto"}</h3><p>{description || "La descripción aparecerá aquí."}</p><b>{price ? formatPrice(price, editor?.currency || "COP") : "$0"}</b></div></article><small>La imagen conserva su proporción para que se vea completa.</small></aside>
        <div className="actions product-editor-actions"><button type="button" className="secondary" onClick={() => setEditor(undefined)}>Cancelar</button><button className="primary" disabled={saving}>{saving ? <LoaderCircle className="spin" size={16}/> : <Plus size={16}/>}Guardar producto</button></div>
      </form>
    </section></div>}
    {profileOpen && <div className="overlay" onMouseDown={event => event.target === event.currentTarget && setProfileOpen(false)}><section className="modal brand-editor-modal"><header><div><h2>Perfil de marca</h2><small>Esta información aparece en tu catálogo público.</small></div><button className="icon" onClick={() => setProfileOpen(false)} aria-label="Cerrar"><X size={18}/></button></header><form onSubmit={saveProfile}>
      <div className="brand-editor-preview">{brandPreview ? <img src={brandPreview} alt="Vista previa del logo"/> : <span><Store size={24}/></span>}<div><b>Vista previa</b><small>JPEG, PNG o WebP · máximo 2 MiB</small></div></div>
      <label>Logo de la marca<input type="file" accept="image/jpeg,image/png,image/webp" onChange={event => chooseBrandImage(event.target.files?.[0] || null)}/></label>
      {catalog.brand_image_url && !removeBrandImage && <button type="button" className="remove-image-link" onClick={() => { setRemoveBrandImage(true); setBrandImage(null); }}>Quitar logo actual</button>}
      {removeBrandImage && <button type="button" className="remove-image-link" onClick={() => setRemoveBrandImage(false)}>Conservar logo actual</button>}
      <label>Nombre de la marca<input required minLength={2} maxLength={120} value={brandName} onChange={event => setBrandName(event.target.value)}/></label>
      <label>Descripción<textarea rows={3} maxLength={500} value={brandDescription} onChange={event => setBrandDescription(event.target.value)} placeholder="Cuéntales a tus clientes sobre tu marca."/></label>
      <label>WhatsApp público de contacto <small>Este número aparecerá en el catálogo para que los clientes puedan escribirte. Usa formato internacional, por ejemplo +573001234567.</small><input type="tel" value={brandWhatsapp} readOnly={!whatsappDisclosureAccepted} onFocus={() => {if(!whatsappDisclosureAccepted)setWhatsappWarningOpen(true)}} onClick={() => {if(!whatsappDisclosureAccepted)setWhatsappWarningOpen(true)}} onChange={event => setBrandWhatsapp(event.target.value)} placeholder="+573001234567"/></label>
      <label className="brand-whatsapp-consent"><input type="checkbox" checked={whatsappOrdersEnabled} onChange={event => setWhatsappOrdersEnabled(event.target.checked)}/><span>Mostrar a mis clientes un enlace para abrir WhatsApp con el resumen del pedido. Catálogos no envía el mensaje: el cliente lo revisa y pulsa enviar.</span></label>
      <label>Instagram <small>Opcional</small><input value={brandInstagram} onChange={event => setBrandInstagram(event.target.value)} placeholder="@tu_marca"/></label>
      <div className="actions"><button type="button" className="secondary" onClick={() => setProfileOpen(false)}>Cancelar</button><button className="primary" disabled={profileSaving}>{profileSaving ? <LoaderCircle className="spin" size={16}/> : <Camera size={15}/>}Guardar perfil</button></div>
    </form></section>{whatsappWarningOpen&&<div className="whatsapp-disclosure-overlay"><section className="whatsapp-disclosure" role="alertdialog" aria-modal="true" aria-labelledby="whatsapp-disclosure-title"><div className="whatsapp-disclosure-mark"><ShieldCheck size={21}/></div><small className="eyebrow">ANTES DE AGREGAR TU NÚMERO</small><h2 id="whatsapp-disclosure-title">Tu WhatsApp será visible en este catálogo</h2><p>Al guardar el perfil, las personas que visiten el enlace público podrán ver este número y escribirte directamente. Catálogos lo muestra porque tú lo agregas; no publica el teléfono en otros espacios.</p><p>Los datos privados del pedido, como el teléfono y la dirección del comprador, se guardan en tu bandeja para que atiendas la compra y no aparecen en el catálogo público. Si el cliente abre el enlace de WhatsApp, él decide enviar el mensaje preparado.</p><label className="whatsapp-disclosure-check"><input type="checkbox" checked={whatsappDisclosureAccepted} onChange={event=>setWhatsappDisclosureAccepted(event.target.checked)}/><span>Entiendo que el número que agregue será público para visitantes de este catálogo.</span></label><div className="actions"><button type="button" className="secondary" onClick={()=>setWhatsappWarningOpen(false)}>Cancelar</button><button type="button" className="primary" disabled={!whatsappDisclosureAccepted} onClick={()=>setWhatsappWarningOpen(false)}>Continuar</button></div></section></div>}</div>}
    {categoryModal && <div className="overlay" onMouseDown={event => event.target === event.currentTarget && setCategoryModal(false)}><section className="modal category-modal"><header><div><h2>Categorías del catálogo</h2><small>Crea categorías y asigna cada producto desde su tarjeta o al editarlo.</small></div><button className="icon" onClick={() => setCategoryModal(false)} aria-label="Cerrar"><X size={18}/></button></header><form className="category-create-form" onSubmit={createCategory}><label>Nueva categoría<input required minLength={2} maxLength={80} value={categoryName} onChange={event => setCategoryName(event.target.value)} placeholder="Ej. Ropa, Accesorios"/></label><button className="primary" disabled={categorySaving}>{categorySaving ? <LoaderCircle className="spin" size={15}/> : <Plus size={15}/>}Crear</button></form>{categories.length ? <div className="category-list">{categories.map(category => <div className="category-row" key={category.id}><span>{category.name}</span><button className="secondary" onClick={() => void renameCategory(category)}><Pencil size={13}/>Renombrar</button><button className="danger-quiet" aria-label={`Eliminar ${category.name}`} onClick={() => void deleteCategory(category)}><Trash2 size={14}/></button></div>)}</div> : <div className="empty category-empty"><h3>Aún no hay categorías</h3><p>Crea una categoría para organizar los productos de este catálogo.</p></div>}</section></div>}
    {deleteStage === "warning" && <div className="catalog-delete-overlay"><section className="catalog-delete-dialog catalog-delete-warning" role="alertdialog" aria-modal="true" aria-labelledby="delete-warning-title" aria-describedby="delete-warning-description"><div className="catalog-delete-icon"><AlertTriangle size={27}/></div><small className="catalog-delete-kicker">ACCIÓN PERMANENTE</small><h2 id="delete-warning-title">Vas a eliminar este catálogo</h2><p id="delete-warning-description">Se eliminará <strong>{catalog.name}</strong> junto con todos sus productos, categorías e imágenes. El enlace público dejará de funcionar.</p><p className="catalog-delete-emphasis">Esta acción es permanente y no se puede deshacer.</p><div className="catalog-delete-actions"><button className="secondary" onClick={() => setDeleteStage(null)}>Cancelar</button><button className="catalog-delete-continue" onClick={() => {setDeleteName("");setDeleteStage("confirm");}}>Entiendo, continuar</button></div></section></div>}
    {deleteStage === "confirm" && <div className="catalog-delete-overlay"><section className="catalog-delete-dialog catalog-delete-final" role="alertdialog" aria-modal="true" aria-labelledby="delete-confirm-title" aria-describedby="delete-confirm-description"><div className="catalog-delete-icon"><Trash2 size={25}/></div><small className="catalog-delete-kicker">CONFIRMACIÓN FINAL</small><h2 id="delete-confirm-title">¿Eliminar “{catalog.name}” definitivamente?</h2><p id="delete-confirm-description">Para confirmar, escribe el nombre exacto del catálogo. Se borrarán también todos sus productos e imágenes.</p><label className="catalog-delete-input-label">Nombre del catálogo<input autoFocus value={deleteName} onChange={event => setDeleteName(event.target.value)} placeholder={catalog.name} onKeyDown={event => {if(event.key === "Enter") event.preventDefault();}}/></label><div className="catalog-delete-actions"><button className="secondary" disabled={deletingCatalog} onClick={() => setDeleteStage(null)}>No, conservar catálogo</button><button className="catalog-delete-danger" disabled={deletingCatalog || deleteName.trim() !== catalog.name} onClick={() => void permanentlyDeleteCatalog()}>{deletingCatalog ? <LoaderCircle className="spin" size={16}/> : <Trash2 size={15}/>}Sí, eliminar permanentemente</button></div></section></div>}
  </div>;
}
