from __future__ import annotations

# Minimal Event Stream taxonomy (v5-aligned, MVP).
EVENT_COMMIT_CREATED = "commit_created"
EVENT_MERGE_CREATED = "merge_created"
EVENT_CONFLICT_DETECTED = "conflict_detected"
EVENT_VERSION_CREATED = "version_created"
EVENT_LIFECYCLE_TRANSITION = "lifecycle_transition"
EVENT_PARSE_COMPLETE = "parse_complete"
EVENT_GRAPH_AUTO_LINK_COMPLETE = "graph_auto_link_complete"
EVENT_SCENE_GRAPH_SNAPSHOT_CREATED = "scene_graph_snapshot_created"

ALL_EVENT_TYPES = {
    EVENT_COMMIT_CREATED,
    EVENT_MERGE_CREATED,
    EVENT_CONFLICT_DETECTED,
    EVENT_VERSION_CREATED,
    EVENT_LIFECYCLE_TRANSITION,
    EVENT_PARSE_COMPLETE,
    EVENT_GRAPH_AUTO_LINK_COMPLETE,
    EVENT_SCENE_GRAPH_SNAPSHOT_CREATED,
}

