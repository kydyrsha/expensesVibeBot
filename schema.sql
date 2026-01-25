create extension if not exists "pgcrypto";

create table if not exists expenses (
    id uuid primary key default gen_random_uuid(),
    user_id bigint not null,
    amount integer not null,
    category text not null,
    created_at timestamp not null
);
