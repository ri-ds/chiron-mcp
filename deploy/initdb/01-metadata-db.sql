-- Runs once, when the Postgres volume is first created. The image's own database
-- ("chiron") is the warehouse; Chiron's metadata gets a database of its own.
CREATE DATABASE chiron_meta OWNER chiron;
