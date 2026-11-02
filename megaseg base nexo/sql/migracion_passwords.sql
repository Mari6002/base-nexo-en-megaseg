-- Reemplaza las contraseñas heredadas por hashes bcrypt.
-- Ejecutar una sola vez sobre la base de datos ya creada.
-- Las contraseñas nunca se guardan en texto plano.
BEGIN;

UPDATE usuarios SET password = '$2b$12$TL/QB/JZ6L7czYY0LyrFSu0QAxwZV6XuDaZFi9dc8K1gqnSA9VDFK'
WHERE usuario = 'admin';

UPDATE usuarios SET password = '$2b$12$OgAA8Wraw6Hw6N23mA3tuecg755xFI9UhYUigUOT6GCfIi4KmAp5y'
WHERE usuario = 'gestor';

UPDATE usuarios SET password = '$2b$12$AHJ7NGJF1aMOnNEjig6Fo.KGccNvcrYEqJQZAqKa68ITHLIoOA/Ru'
WHERE usuario = 'soporte';

UPDATE usuarios SET password = '$2b$12$vBAdYTb1ut67p8lNXzNvauh/oH5oyIY7a6bOnk/N6XGrIwHBShoRC'
WHERE usuario = 'cliente';

COMMIT;

-- Comprobación: no debe devolver contraseñas en texto plano.
SELECT id, usuario, LEFT(password, 4) AS hash_tipo,
       CASE
           WHEN password LIKE '$2a$%'
             OR password LIKE '$2b$%'
             OR password LIKE '$2y$%'
           THEN 'bcrypt'
           ELSE 'REVISAR'
       END AS estado_password
FROM usuarios
ORDER BY id;
