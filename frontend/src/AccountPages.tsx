import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, Boxes, CheckCircle2, LoaderCircle, Mail } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { supabase, sbReady } from "./supabase";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!sbReady) { toast.error("No se pudo conectar en este momento. Inténtalo de nuevo más tarde."); return; }
    setBusy(true);
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/restablecer-contrasena`,
    });
    setBusy(false);
    if (error) { toast.error("No pudimos enviar las instrucciones. Inténtalo de nuevo."); return; }
    setSent(true);
  }

  return <main className="login"><section className="login-card account-card">
    <Link className="brand account-brand" to="/"><span className="mark"><Boxes size={18}/></span>Catálogos</Link>
    {sent ? <><span className="account-status-icon"><CheckCircle2 size={20}/></span><h1>Revisa tu correo</h1><p>Si existe una cuenta asociada a <strong>{email}</strong>, recibirás un enlace para cambiar tu contraseña.</p><Link className="primary full account-action" to="/login">Volver al inicio de sesión</Link></> : <>
      <small className="eyebrow">RECUPERACIÓN DE CUENTA</small><h1>¿Olvidaste tu contraseña?</h1><p>Escribe el correo de tu cuenta y te enviaremos un enlace para crear una nueva contraseña.</p>
      <form className="account-form" onSubmit={submit}><label>Correo electrónico<input required type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="nombre@empresa.com"/></label><button className="primary full" disabled={busy}>{busy ? <LoaderCircle size={16} className="spin"/> : <Mail size={16}/>}Enviar instrucciones</button></form>
      <Link className="account-back" to="/login"><ArrowLeft size={14}/> Volver al inicio de sesión</Link>
    </>}
  </section></main>;
}

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  const [hasSession, setHasSession] = useState(false);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    supabase.auth.getSession().then(({ data }) => {
      if (active) { setHasSession(Boolean(data.session)); setReady(true); }
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (active && session) { setHasSession(true); setReady(true); }
    });
    return () => { active = false; subscription.unsubscribe(); };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password !== confirm) { toast.error("Las contraseñas no coinciden."); return; }
    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password });
    setBusy(false);
    if (error) { toast.error("No pudimos cambiar la contraseña. Solicita un enlace nuevo e inténtalo otra vez."); return; }
    toast.success("Contraseña actualizada.");
    navigate("/login", { replace: true });
  }

  return <main className="login"><section className="login-card account-card">
    <Link className="brand account-brand" to="/"><span className="mark"><Boxes size={18}/></span>Catálogos</Link>
    {!ready ? <div className="loading-box"><LoaderCircle className="spin"/></div> : hasSession ? <>
      <small className="eyebrow">SEGURIDAD DE LA CUENTA</small><h1>Crea una nueva contraseña</h1><p>Elige una contraseña nueva para volver a acceder a tu cuenta.</p>
      <form className="account-form" onSubmit={submit}><label>Nueva contraseña<input required minLength={8} type="password" autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} placeholder="Mínimo 8 caracteres"/></label><label>Confirmar contraseña<input required minLength={8} type="password" autoComplete="new-password" value={confirm} onChange={event => setConfirm(event.target.value)} placeholder="Repite la contraseña"/></label><button className="primary full" disabled={busy}>{busy ? <LoaderCircle size={16} className="spin"/> : null}Guardar contraseña</button></form>
    </> : <><small className="eyebrow">ENLACE NO DISPONIBLE</small><h1>Solicita un enlace nuevo</h1><p>Abre el enlace de recuperación que enviamos a tu correo. Si ya venció, solicita otro para continuar.</p><Link className="primary full account-action" to="/recuperar-contrasena">Solicitar enlace nuevo</Link><Link className="account-back" to="/login"><ArrowLeft size={14}/> Volver al inicio de sesión</Link></>}
  </section></main>;
}
