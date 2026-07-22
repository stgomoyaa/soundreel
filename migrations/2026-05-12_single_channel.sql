-- ════════════════════════════════════════════════════════════════
-- Migración: dual-channel → single-channel
-- ════════════════════════════════════════════════════════════════
--
-- Antes: uploads.channel guardaba '1' o '2' (dos canales temáticos distintos).
-- Después: 1 solo canal. La columna se mantiene con DEFAULT 'main'
-- para no romper rows históricos ni queries existentes.
--
-- Idempotente: se puede correr varias veces sin efecto adicional.
--
-- Aplicar:
--     psql $DATABASE_URL -f migrations/2026-05-12_single_channel.sql
-- ════════════════════════════════════════════════════════════════

BEGIN;

-- 1) Set DEFAULT 'main' (para nuevos INSERTs que omitan la columna).
ALTER TABLE uploads
    ALTER COLUMN channel SET DEFAULT 'main';

-- 2) Normaliza rows existentes con channel='1' o '2' → 'main'.
UPDATE uploads
SET channel = 'main'
WHERE channel IN ('1', '2');

COMMIT;

-- Verificación (no transaccional):
SELECT channel, COUNT(*) AS rows FROM uploads GROUP BY channel;
