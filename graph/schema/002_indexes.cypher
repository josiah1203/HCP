// Performance indexes — org-scoped traversal and lookups

CREATE INDEX hardware_object_org IF NOT EXISTS FOR (h:HardwareObject) ON (h.org_id);
CREATE INDEX version_org IF NOT EXISTS FOR (v:Version) ON (v.org_id);
CREATE INDEX version_object IF NOT EXISTS FOR (v:Version) ON (v.object_id);
CREATE INDEX project_org IF NOT EXISTS FOR (p:Project) ON (p.org_id);
CREATE INDEX requirement_org IF NOT EXISTS FOR (r:Requirement) ON (r.org_id);
CREATE INDEX firmware_org IF NOT EXISTS FOR (f:Firmware) ON (f.org_id);
CREATE INDEX part_mpn IF NOT EXISTS FOR (p:Part) ON (p.mpn);
CREATE INDEX supplier_name IF NOT EXISTS FOR (s:Supplier) ON (s.name);
