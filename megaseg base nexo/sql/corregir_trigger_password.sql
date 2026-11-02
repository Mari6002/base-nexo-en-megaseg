-- Evita volver a cifrar un hash bcrypt durante UPDATE o INSERT.
-- Ejecutar una sola vez en la base PostgreSQL conectada a Render.
BEGIN;

CREATE OR REPLACE FUNCTION fn_cifrar_password()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.password !~ '^\$2[aby]\$[0-9]{2}\$' THEN
        NEW.password := crypt(NEW.password, gen_salt('bf'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMIT;
