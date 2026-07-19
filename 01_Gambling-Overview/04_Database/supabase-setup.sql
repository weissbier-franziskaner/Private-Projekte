-- Supabase SQL für die Spiel-Tracker-Tabelle
create extension if not exists pgcrypto;

create table if not exists public.game_results (
  id uuid primary key default gen_random_uuid(),
  game text not null,
  participants text not null,
  winner text not null,
  created_at timestamptz not null default now()
);

alter table public.game_results enable row level security;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'game_results'
      and policyname = 'Allow public insert'
  ) then
    create policy "Allow public insert"
      on public.game_results
      for insert
      to anon
      with check (true);
  end if;
end
$$;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'game_results'
      and policyname = 'Allow public select'
  ) then
    create policy "Allow public select"
      on public.game_results
      for select
      to anon
      using (true);
  end if;
end
$$;