-- Ugentlig udløser af AI Radar-kørslen fra databasen (Supabase pg_cron +
-- pg_net). Ligger uden for migrations/, fordi pg_cron og pg_net er
-- Supabase-specifikke og ikke findes i CI's PostgreSQL. Køres manuelt pr.
-- miljø (SQL editor eller Management API), efter at API'et med
-- worker_trigger_keys er deployet.
--
-- Nøglen gemmes i Supabase Vault (krypteret); API'et kender kun dens
-- SHA-256-hash (worker_trigger_keys). Erstat :token med en lang tilfældig
-- værdi (fx `openssl rand -hex 32`) og :api_url med API'ets URL inkl. /api/v1.

create extension if not exists pg_cron;
create extension if not exists pg_net;

select vault.create_secret(:'token', 'ai_radar_worker_token', 'X-Worker-Token til ugentlig kørsel');
insert into worker_trigger_keys (token_sha256, note)
values (encode(extensions.digest(:'token', 'sha256'), 'hex'), 'pg_cron ugentlig kørsel');

-- Render free tier sover: et ping vækker API'et, kørslen starter fem
-- minutter senere, og et nyt forsøg kl. 05:20 fanger en fejlet opvågning
-- (en kørsel, der allerede er i gang, afvises med 409 og gør ingen skade).
-- Mandag 04:55/05:00/05:20 UTC = 06:55/07:00/07:20 dansk sommertid.
select cron.schedule('ai-radar-wake', '55 4 * * 1', format(
  $$select net.http_get(url := %L, timeout_milliseconds := 90000)$$,
  :'api_url' || '/health'));

select cron.schedule('ai-radar-weekly-run', '0 5 * * 1', format(
  $$select net.http_post(
      url := %L,
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'X-Worker-Token',
        (select decrypted_secret from vault.decrypted_secrets
          where name = 'ai_radar_worker_token')),
      body := '{"force_all": false}'::jsonb,
      timeout_milliseconds := 90000)$$,
  :'api_url' || '/runs'));

select cron.schedule('ai-radar-weekly-run-retry', '20 5 * * 1', format(
  $$select net.http_post(
      url := %L,
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'X-Worker-Token',
        (select decrypted_secret from vault.decrypted_secrets
          where name = 'ai_radar_worker_token')),
      body := '{"force_all": false}'::jsonb,
      timeout_milliseconds := 90000)$$,
  :'api_url' || '/runs'));
