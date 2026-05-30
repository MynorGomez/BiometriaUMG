-- ============================================
-- INSERTAR 5 DOCENTES EN LA BASE DE DATOS
-- ============================================

-- 1. INSERTAR PERSONAS (docentes)
INSERT INTO personas (nombre, apellido, carnet, correo_personal, estado) 
VALUES 
  ('Juan', 'Pérez', '1001-2024-00001', 'juan.perez@email.com', 'activo'),
  ('María', 'González', '1001-2024-00002', 'maria.gonzalez@email.com', 'activo'),
  ('Carlos', 'López', '1001-2024-00003', 'carlos.lopez@email.com', 'activo'),
  ('Ana', 'Martínez', '1001-2024-00004', 'ana.martinez@email.com', 'activo'),
  ('Luis', 'Rodríguez', '1001-2024-00005', 'luis.rodriguez@email.com', 'activo');

-- 2. ASIGNAR JORNADA A CADA DOCENTE (jornada = 36 = Domingo)
-- Obtener los IDs de las personas recién insertadas
-- Asumiendo que se insertaron con IDs del 9 al 13 (después del ID 8 que ya existe)

INSERT INTO roles_persona (id_persona, id_rol, id_jornada)
VALUES
  (9, 2, 36),   -- Juan Pérez - catedrático (id_rol=2), Domingo
  (10, 2, 36),  -- María González - catedrático, Domingo
  (11, 2, 36),  -- Carlos López - catedrático, Domingo
  (12, 2, 36),  -- Ana Martínez - catedrático, Domingo
  (13, 2, 36);  -- Luis Rodríguez - catedrático, Domingo

-- 3. (OPCIONAL) CREAR USUARIOS PARA LOS DOCENTES
-- Descomenta si quieres crear usuarios también
-- Las contraseñas están hasheadas (scrypt)

/*
INSERT INTO usuarios (id_persona, username, password)
VALUES
  (9, 'juan.perez', 'scrypt:32768:8:1$XqeGMgjrSfsSr2Ku$583b715fe67f2ddcf2b5c2f7e58bf964bf9aaecdecafc11f28adf980f95d1119d03dc81edb4461439eb883c4118e8da883c9908be35c1d9e21ebcd82d915d362'),
  (10, 'maria.gonzalez', 'scrypt:32768:8:1$EQSkR9wJ3pyuICJb$4afea7f1d02b49e1dfbb13b837f472ef8bc37d8a8f942258246599e801b2bcc0efbdaf3970f12e7d79d5f6c3d5901d4d74bf350252833b5dd5f3fc076c732f1a'),
  (11, 'carlos.lopez', 'scrypt:32768:8:1$Z038J4SluIhuEcvt$963758fbcfa61ee2f5e99fd29b6434885cc788fa97330c36916c4d25b639af1b2e870425e122d449ecac0db282c9a817de9ff8248040d41e212c47f943931c42'),
  (12, 'ana.martinez', 'scrypt:32768:8:1$XqeGMgjrSfsSr2Ku$583b715fe67f2ddcf2b5c2f7e58bf964bf9aaecdecafc11f28adf980f95d1119d03dc81edb4461439eb883c4118e8da883c9908be35c1d9e21ebcd82d915d362'),
  (13, 'luis.rodriguez', 'scrypt:32768:8:1$EQSkR9wJ3pyuICJb$4afea7f1d02b49e1dfbb13b837f472ef8bc37d8a8f942258246599e801b2bcc0efbdaf3970f12e7d79d5f6c3d5901d4d74bf350252833b5dd5f3fc076c732f1a');
*/

-- ============================================
-- INSTRUCCIONES DE USO:
-- ============================================
-- 1. Abre MySQL Workbench o línea de comandos de MySQL
-- 2. Conecta a la base de datos: USE sistema_biometrico_umg;
-- 3. Copia y ejecuta los primeros 2 INSERT (personas y roles_persona)
-- 4. Si quieres crear usuarios, descomenta la parte 3 y ejecuta también
-- 5. Verifica: SELECT * FROM personas WHERE carnet LIKE '1001-2024%';
--
-- NOTAS:
-- - Los IDs de personas se auto-incrementan, ajusta si es necesario
-- - id_rol = 2 es el rol 'catedrático'
-- - id_jornada = 36 es 'Domingo'
-- - Las contraseñas de usuarios son ejemplos; puedes generar las tuyas
-- ============================================
