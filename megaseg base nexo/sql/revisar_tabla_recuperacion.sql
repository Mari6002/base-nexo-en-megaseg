-- Revisión opcional y no destructiva de una tabla antigua.
-- Este archivo NO borra datos ni tablas.
-- Ejecutarlo solo si quieres comprobar si la tabla existe y cuántos registros tiene.
SET client_encoding = 'UTF8';

SELECT
    to_regclass('public.password_reset_tokens') AS tabla,
    CASE
        WHEN to_regclass('public.password_reset_tokens') IS NULL THEN 0
        ELSE (SELECT COUNT(*) FROM password_reset_tokens)
    END AS registros;
