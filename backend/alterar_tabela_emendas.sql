-- Permitir deputado_id nulo na tabela emendas_parlamentares
-- Para suportar emendas de comissão (EMC) que não têm deputado autor

ALTER TABLE emendas_parlamentares 
ALTER COLUMN deputado_id DROP NOT NULL;

-- Verificar a alteração
\d emendas_parlamentares;
