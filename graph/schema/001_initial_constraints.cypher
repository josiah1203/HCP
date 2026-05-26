// Neo4j initial constraints — apply via: cypher-shell -f graph/schema/001_initial_constraints.cypher

CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Org) REQUIRE o.org_id IS UNIQUE;
CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.project_id IS UNIQUE;
CREATE CONSTRAINT object_id IF NOT EXISTS FOR (h:HardwareObject) REQUIRE h.object_id IS UNIQUE;
CREATE CONSTRAINT version_id IF NOT EXISTS FOR (v:Version) REQUIRE v.version_id IS UNIQUE;
CREATE CONSTRAINT part_mpn_mfr IF NOT EXISTS FOR (p:Part) REQUIRE (p.mpn, p.manufacturer) IS UNIQUE;
