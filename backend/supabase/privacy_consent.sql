-- Registra aceptación explícita con marca de tiempo del servidor.
-- Ejecutar en Supabase SQL Editor antes de desplegar la versión que exige consentimiento.
create table if not exists public.privacy_consents (
    user_id uuid not null references auth.users(id) on delete cascade,
    policy_version text not null,
    accepted_at timestamptz not null default now(),
    primary key (user_id, policy_version)
);

alter table public.privacy_consents enable row level security;
revoke all on public.privacy_consents from anon, authenticated;

-- Bloquea los registros que no envíen aceptación expresa desde Supabase Auth.
create or replace function public.record_signup_privacy_consent()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    consent jsonb;
    version text;
begin
    consent := new.raw_user_meta_data -> 'privacy_consent';
    version := consent ->> 'policy_version';
    if consent ->> 'accepted' is distinct from 'true' or version is distinct from '2026-10-27-v2' then
        raise exception 'Debe aceptar el aviso de privacidad vigente para crear una cuenta';
    end if;
    insert into public.privacy_consents (user_id, policy_version, accepted_at)
    values (new.id, version, now())
    on conflict (user_id, policy_version) do nothing;
    return new;
end;
$$;

drop trigger if exists require_privacy_consent_on_signup on auth.users;
create trigger require_privacy_consent_on_signup
    after insert on auth.users
    for each row execute function public.record_signup_privacy_consent();
