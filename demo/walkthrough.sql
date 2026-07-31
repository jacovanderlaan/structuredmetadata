-- ============================================================================
-- MDDE metamodel walkthrough -- run against demo/mdde_meta_demo.duckdb
--     duckdb demo/mdde_meta_demo.duckdb < demo/walkthrough.sql
-- 15 queries, one story: the model is data, so every question is a query.
-- Every query is verified against the shipped schema.
-- ============================================================================

-- [1] The lay of the land: how big is the metamodel, how much is in use here?
SELECT count(*) AS tables_total,
       count(*) FILTER (WHERE estimated_size > 0) AS tables_with_rows
FROM duckdb_tables() WHERE schema_name = 'metadata';

-- [2] The four hubs everything hangs off
SELECT 'models' AS hub, count(*) AS n FROM metadata.model
UNION ALL SELECT 'entities',   count(*) FROM metadata.entity
UNION ALL SELECT 'attributes', count(*) FROM metadata.attribute
UNION ALL SELECT 'mappings',   count(*) FROM metadata.entity_mapping
ORDER BY n DESC;

-- [3] Containment: model -> entities -> attribute counts (ch. 1)
SELECT e.model_id, e.entity_name, count(a.attribute_id) AS attributes
FROM metadata.entity e
LEFT JOIN metadata.attribute a ON a.entity_id = e.entity_id
GROUP BY 1, 2
ORDER BY 1, 3 DESC
LIMIT 20;

-- [4] Identifiers as first-class objects (ch. 1)
SELECT i.entity_id, i.name AS identifier, i.identifier_type, i.is_primary,
       count(ia.attribute_id) AS member_columns
FROM metadata.identifier_def i
LEFT JOIN metadata.identifier_attribute ia ON ia.identifier_id = i.identifier_id
GROUP BY 1, 2, 3, 4;

-- [5] Governance lives ON the attribute: PII classification per entity (ch. 1)
SELECT e.entity_name, count(*) AS pii_attributes
FROM metadata.attribute a
JOIN metadata.entity e ON e.entity_id = a.entity_id
WHERE a.is_pii
GROUP BY 1 ORDER BY 2 DESC LIMIT 10;

-- [6] The FROM clause as data: joins with type and cardinality (ch. 2)
SELECT e.entity_name AS target, em.source_table, em.join_type, em.join_cardinality
FROM metadata.entity_mapping em
JOIN metadata.entity e ON e.entity_id = em.entity_id
LIMIT 20;

-- [7] Column-level lineage: the SELECT list as rows (ch. 2)
SELECT tgt.entity_name AS target, src.entity_name AS source,
       count(*) AS mapped_columns
FROM metadata.attribute_mapping am
JOIN metadata.entity tgt ON tgt.entity_id = am.target_entity_id
LEFT JOIN metadata.entity src ON src.entity_id = am.source_entity_id
GROUP BY 1, 2
ORDER BY 3 DESC
LIMIT 15;

-- [8] Impact analysis, the query a SQL-string can't answer (ch. 2):
--     change this function -> which entities/attributes are touched?
SELECT f.name AS function, f.category,
       count(DISTINCT a.entity_id) AS entities_affected
FROM metadata.function_def f
JOIN metadata.attribute a ON a.function_id = f.function_id
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10;

-- [9] Expressions as data: transform types across all attributes (ch. 2)
SELECT transform_type, count(*) AS attributes
FROM metadata.attribute
WHERE transform_type IS NOT NULL
GROUP BY 1 ORDER BY 2 DESC;

-- [10] Time as an explicit decision -- even "none" is recorded (ch. 3)
SELECT selection_type, count(*) AS entities
FROM metadata.entity_time_selection
GROUP BY 1 ORDER BY 2 DESC;

-- [11] Stereotypes: the metamodel's extension mechanism as rows (ch. 1)
SELECT metaclass, count(*) AS stereotypes
FROM metadata.stereotype_def
GROUP BY 1 ORDER BY 2 DESC;

-- [12] Relationships with cardinality, as data (ch. 1)
SELECT cardinality, count(*) AS n
FROM metadata.relationship_def
GROUP BY 1 ORDER BY 2 DESC;

-- [13] Entity classification: what KINDS of entity does the model hold? (ch. 1)
SELECT entity_type, query_type, count(*) AS n
FROM metadata.entity
GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15;

-- [14] The empty tables are a feature: capabilities you haven't adopted
--      cost nothing (intro chapter's "core vs optional")
SELECT count(*) AS optional_capacity_unused
FROM duckdb_tables()
WHERE schema_name = 'metadata' AND estimated_size = 0;

-- [15] Self-reference: the metamodel model, in the metamodel
SELECT * FROM metadata.model WHERE model_id = 'mdde_metadata';
