// Remaining node uniqueness constraints per HCP §10.1

CREATE CONSTRAINT supplier_name IF NOT EXISTS FOR (s:Supplier) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT requirement_id IF NOT EXISTS FOR (r:Requirement) REQUIRE r.req_id IS UNIQUE;
CREATE CONSTRAINT firmware_version_id IF NOT EXISTS FOR (f:Firmware) REQUIRE f.version_id IS UNIQUE;
