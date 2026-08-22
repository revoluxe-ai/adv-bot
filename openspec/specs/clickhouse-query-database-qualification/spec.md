## Purpose

Требования к явной квалификации database в тексте ClickHouse SQL для
рабочего контура (`default_db.<object>`) и к proof через issued SQL
(не полный mock producer'а).

## Requirements

### Requirement: Working-contour ClickHouse SQL qualifies database in query text
Application-owned ClickHouse queries that address objects in the working
database MUST include an explicit database qualification in the SQL text.
For the current working contour the qualified form MUST be
`default_db.<object>` (table, materialized view, or equivalent). Relying only
on the ClickHouse client session database MUST NOT be treated as sufficient
addressing for those queries.

#### Scenario: Keyword cluster aggregate query uses qualified MV name
- **WHEN** the application builds the ClickHouse query used by
  `get_keyword_statistic_clickhouse` (or its successor owner of that SQL)
- **THEN** the issued SQL text MUST contain `default_db.mv_clusters_daily_agg`
- **AND THEN** the issued SQL text MUST NOT address that MV as an unqualified
  `mv_clusters_daily_agg` without the `default_db.` prefix

#### Scenario: Same-class regression is repaired with qualification
- **WHEN** a same-class ClickHouse query path is found where a working-contour
  object was addressed without a database prefix in the SQL text
- **THEN** that path MUST be updated so the issued SQL uses
  `default_db.<object>`
- **AND THEN** product aggregate formulas MUST remain unchanged except for
  the addressing qualification

### Requirement: Qualification changes are proven via issued SQL
When ClickHouse SQL text is rewritten for database qualification (or a seam
touches that SQL), tests MUST prove the qualification on the issued SQL.
A full mock of the function whose SQL was changed MUST NOT be accepted as
sole proof of the rewrite.

#### Scenario: Unit contract asserts default_db in issued SQL
- **WHEN** a unit test covers a repaired qualification path
- **THEN** the test MUST capture or inspect the SQL string passed to the
  ClickHouse client query API
- **AND THEN** the assertion MUST require the working-contour database
  qualification (`default_db.`) for the addressed object
- **AND THEN** the test MUST NOT replace that proof by mocking away the entire
  SQL-producing callable as the only check
