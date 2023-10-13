create table
  globals (
    gold bigint primary key generated always as identity,
    red_ml bigint not null default 0,
    green_ml bigint not null default 0,
    blue_ml bigint not null default 0,
    dark_ml bigint not null default 0,
    potion_inventory bigint not null default 0
  );

create table
  potions (
    index bigint primary key generated always as identity,
    name text not null,
    potion_type integer[] not null check (array_length(potion_type, 1) = 4),
    inventory integer default 0 not null,
    sku text not null
  )

insert into
  potions (name, potion_type)
values
  ('red', array[100, 0, 0, 0], 'RED_POTION'),
  ('green', array[0, 100, 0, 0], 'GREEN_POTION'),
  ('blue', array[0, 0, 100, 0], 'BLUE_POTION'),
  ('dark', array[0, 0, 0, 100], 'DARK_POTION'),
  ('purple', array[50, 0, 50, 0], 'PURPLE_POTION'),
  ('yellow', array[50, 50, 0, 0], 'YELLOW_POTION'),
  ('teal', array[0, 50, 50, 0], 'TEAL_POTIONS'),
  ('dark_red', array[50, 0, 0, 50], 'DARK_RED_POTION'),
  ('dark_green', array[0, 50, 0, 50], 'DARK_GREEN_POTION'),
  ('dark_blue', array[0, 0, 50, 50], 'DARK_BLUE_POTION')

  create table
  Carts (
    cart_id bigint primary key generated always as identity,
    name text not null
  )

  create table
  Cart_items (
    cart_id int not null,
    sku text not null,
    quantity int not null,
    primary key (cart_id, sku)
  );