-- Migrationsbaseline for AI Radar.
-- Konventioner (Technical Master §5): alle primære tabeller bruger UUID,
-- created_at/updated_at og auditmetadata; timestamps gemmes i UTC.
-- Domænetabellerne (Source, Document, Claim, ...) tilføjes i Slice 1+.

create extension if not exists "pgcrypto";

-- Fælles trigger-funktion, som senere migrations binder til updated_at.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;
