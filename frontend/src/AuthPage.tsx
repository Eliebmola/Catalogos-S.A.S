import { useState, type FormEvent } from "react";
import { Boxes, LoaderCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { supabase } from "./supabase";
import { Link } from "react-router-dom";
import { privacyIdentityComplete, privacyPolicyVersion } from "./privacy";
import { LanguageSelect, useI18n } from "./i18n";

export function AuthPage() {
  const {t}=useI18n();
  const [mode, setMode] = useState<"login" | "signup">(() => new URLSearchParams(window.location.search).get("mode") === "signup" ? "signup" : "login");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmationPending, setConfirmationPending] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const navigate = useNavigate();

  async function submit(event: FormEvent) {
    event.preventDefault();
    const configured = Boolean(import.meta.env.VITE_SUPABASE_URL && import.meta.env.VITE_SUPABASE_ANON_KEY);
    if (!configured) {
      toast.error("Configura VITE_SUPABASE_URL y VITE_SUPABASE_ANON_KEY en .env.local.");
      return;
    }
    if (mode === "signup" && password !== confirmPassword) {
      toast.error("Las contraseñas no coinciden.");
      return;
    }
    if (mode === "signup" && !privacyIdentityComplete) {
      toast.error("El aviso de privacidad aún requiere los datos de identificación y contacto del responsable.");
      return;
    }
    if (mode === "signup" && !privacyAccepted) {
      toast.error("Debes leer y aceptar el aviso de privacidad para crear tu cuenta.");
      return;
    }
    setBusy(true);
    const requestedPath = new URLSearchParams(window.location.search).get("next");
    const destination = requestedPath?.startsWith("/") && !requestedPath.startsWith("//") ? requestedPath : "/dashboard";
    if (mode === "login") {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      setBusy(false);
      if (error) toast.error(error.message);
      else navigate(destination, { replace: true });
      return;
    }
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${window.location.origin}/login`, data: { full_name: fullName.trim(), privacy_consent: { accepted: true, policy_version: privacyPolicyVersion } } },
    });
    setBusy(false);
    if (error) {
      toast.error(error.message);
      return;
    }
    if (data.session) navigate(destination, { replace: true });
    else setConfirmationPending(true);
  }

  return <main className="login"><style>{`.auth-switch{display:flex;align-items:center;justify-content:center;gap:5px;color:#8791a0;font-size:10px}.auth-switch button{border:0;background:none;padding:3px;color:#4f46e5;font-size:10px;font-weight:600}.auth-switch button:hover{text-decoration:underline}.login-card>p strong{color:#344054;font-weight:600}`}</style><form className="login-card" onSubmit={submit}>
    <div className="auth-topline"><Link className="brand account-brand" to="/"><span className="mark"><Boxes size={18} /></span>Catálogos</Link><LanguageSelect/></div>
    <small className="eyebrow">{t("loginSellerNote").toLocaleUpperCase()}</small>
    {confirmationPending ? <>
      <h1>{t("reviewEmail")}</h1>
      <p>Enviamos un enlace de confirmación a <strong>{email}</strong>. Confirma tu cuenta y luego inicia sesión para administrar tus catálogos.</p>
      <button type="button" className="secondary full" onClick={() => { setConfirmationPending(false); setMode("login"); }}>Volver al inicio de sesión</button>
    </> : <>
      <h1>{mode === "login" ? t("welcome") : t("createSellerAccount")}</h1>
      <p>{mode === "login" ? t("loginText") : t("registerText")}</p>
      {mode === "signup" && <label>{t("fullName")}<input required minLength={2} maxLength={120} autoComplete="name" value={fullName} onChange={event=>setFullName(event.target.value)} placeholder={t("fullName")} /></label>}
      <label>{t("email")}<input required type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="nombre@empresa.com" /></label>
      <label>{t("password")}<input required minLength={8} type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={event => setPassword(event.target.value)} placeholder={t("password")} /></label>
      {mode === "login" && <Link className="forgot-password-link" to="/recuperar-contrasena">{t("forgotPassword")}</Link>}
      {mode === "signup" && <label>{t("confirmPassword")}<input required minLength={8} type="password" autoComplete="new-password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} placeholder={t("confirmPassword")} /></label>}
      {mode === "signup" && <div className="privacy-consent-choice"><input id="privacy-accept" type="checkbox" checked={privacyAccepted} onChange={event => setPrivacyAccepted(event.target.checked)} /><label htmlFor="privacy-accept">{t("privacyConsent")} <Link to="/aviso-de-privacidad" target="_blank">{t("privacyNotice")}</Link>.</label></div>}
      <button className="primary full" disabled={busy || (mode === "signup" && (!privacyAccepted || !privacyIdentityComplete))}>{busy && <LoaderCircle className="spin" size={16} />}{mode === "login" ? t("signIn") : t("createAccount")}</button>
      <div className="auth-switch">{mode === "login" ? "¿Aún no tienes cuenta?" : "¿Ya tienes una cuenta?"}<button type="button" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setPassword(""); setConfirmPassword(""); setPrivacyAccepted(false); }}>{mode === "login" ? t("register") : t("signIn")}</button></div>
    </>}
    <small className="auth-note">{t("loginSellerNote")}</small>
    <div className="auth-legal-links"><Link className="privacy-document-link auth-privacy-link" to="/aviso-de-privacidad">{t("privacyNotice")}</Link><Link className="privacy-document-link auth-privacy-link" to="/terminos">Términos y condiciones</Link><Link className="privacy-document-link auth-privacy-link" to="/cookies">Cookies</Link></div>
  </form></main>;
}
