-- Kundecenter-kildepakke (2026-10): flytter radarens kilder fra generel
-- tech-/leverandørnyhed til AI i kundeservice og kundecentre.
--
-- Køres manuelt i Supabase → SQL Editor. Idempotent: en kilde med samme
-- endpoint_url oprettes ikke to gange.
--
-- Feedene kunne ikke testes fra udviklingsmiljøet. Første kørsel viser
-- hentefejl pr. kilde; en kilde der fejler, sættes inaktiv i Admin → Kilder.
-- Bing News-feeds giver danske søgeresultater; deres links redirecter til
-- den oprindelige artikel, som hentes som sit eget dokument.

insert into sources
  (name, base_url, source_type, retrieval_method, endpoint_url, country_code,
   frequency, access_class, active, next_check_at, notes)
select v.name, v.base_url, v.source_type::source_type, 'rss'::retrieval_method, v.endpoint_url,
       v.country_code, 'weekly'::source_frequency, 'public'::access_class, true, now(),
       'Kundecenter-kildepakke 2026-10'
from (values
  ('CX Network – Contact Center', 'https://www.cxnetwork.com', 'media',
   'https://www.cxnetwork.com/rss/categories/contact-center', null),
  ('CCW Digital – Tools & Technologies', 'https://europe.customercontactweekdigital.com', 'media',
   'https://europe.customercontactweekdigital.com/rss/categories/tools-technologies', null),
  ('Call Centre Helper', 'https://www.callcentrehelper.com', 'media',
   'https://www.callcentrehelper.com/feed', null),
  ('Bing News: kundeservice + kunstig intelligens', 'https://www.bing.com/news', 'media',
   'https://www.bing.com/news/search?q=kundeservice+%22kunstig+intelligens%22&format=rss&setlang=da&cc=DK', 'DK'),
  ('Bing News: kundecenter AI', 'https://www.bing.com/news', 'media',
   'https://www.bing.com/news/search?q=kundecenter+AI&format=rss&setlang=da&cc=DK', 'DK'),
  ('Bing News: chatbot kundeservice', 'https://www.bing.com/news', 'media',
   'https://www.bing.com/news/search?q=chatbot+kundeservice&format=rss&setlang=da&cc=DK', 'DK'),
  ('Bing News: AI kundeservice Norden', 'https://www.bing.com/news', 'media',
   'https://www.bing.com/news/search?q=%22customer+service%22+AI+Denmark+OR+Nordic&format=rss', null)
) as v(name, base_url, source_type, endpoint_url, country_code)
where not exists (select 1 from sources s where s.endpoint_url = v.endpoint_url);

-- Rene leverandør-/forskningsblogs uden kundeserviceperspektiv sættes på
-- pause. Version2 beholdes: det nye relevansfilter sorterer generelle
-- artikler fra med den billige model.
update sources set active = false,
  notes = coalesce(notes || ' · ', '') || 'Pauset 2026-10: ikke kundecenter-relevant'
where active and endpoint_url ilike '%aws.amazon.com%';

select name, active, frequency, endpoint_url from sources order by active desc, name;
