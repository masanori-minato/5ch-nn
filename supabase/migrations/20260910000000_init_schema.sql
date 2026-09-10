-- 5ch-nn: initial schema for persisting collected thread data.
--
-- Design: threads (stable identity per board+dat_id) is separate from
-- thread_snapshots (one row per collect run per thread), so history
-- accumulates over time instead of being overwritten like state/threads.json
-- currently is. All writes are expected to come from the backend (GitHub
-- Actions using the service_role key), so RLS is enabled with no policies:
-- nothing is reachable via the anon/public key.

create table if not exists public.boards (
  key  text primary key,
  name text not null
);

insert into public.boards (key, name) values
  ('newsplus',   'ニュース速報+'),
  ('news',       'ニュース速報'),
  ('mnewsplus',  '芸能・スポーツ速報+'),
  ('news4plus',  '東アジアニュース+'),
  ('poverty',    'ニュース速報(嫌儲)')
on conflict (key) do update set name = excluded.name;

create table if not exists public.threads (
  id                bigint generated always as identity primary key,
  board_key         text not null references public.boards(key),
  dat_id            text not null,
  title             text not null,
  url               text not null,
  thread_created_at timestamptz not null,
  first_seen_at     timestamptz not null default now(),
  unique (board_key, dat_id)
);

create index if not exists threads_board_key_idx on public.threads (board_key);

create table if not exists public.thread_snapshots (
  id           bigint generated always as identity primary key,
  thread_id    bigint not null references public.threads(id) on delete cascade,
  collected_at timestamptz not null,
  res_count    integer not null,
  velocity     numeric(10, 2) not null,
  unique (thread_id, collected_at)
);

create index if not exists thread_snapshots_thread_id_collected_at_idx
  on public.thread_snapshots (thread_id, collected_at desc);
create index if not exists thread_snapshots_collected_at_idx
  on public.thread_snapshots (collected_at desc);

alter table public.boards enable row level security;
alter table public.threads enable row level security;
alter table public.thread_snapshots enable row level security;
