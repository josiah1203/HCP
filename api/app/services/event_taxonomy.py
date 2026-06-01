from __future__ import annotations

# Event stream taxonomy (v5-aligned, Phase 0.5 beta).

# Version control / object lifecycle
EVENT_COMMIT_CREATED = "commit_created"
EVENT_MERGE_CREATED = "merge_created"
EVENT_CONFLICT_DETECTED = "conflict_detected"
EVENT_VERSION_CREATED = "version_created"
EVENT_LIFECYCLE_TRANSITION = "lifecycle_transition"
EVENT_PARSE_COMPLETE = "parse_complete"
EVENT_GRAPH_AUTO_LINK_COMPLETE = "graph_auto_link_complete"
EVENT_SCENE_GRAPH_SNAPSHOT_CREATED = "scene_graph_snapshot_created"

# Collaboration (Phase 0.5 beta — polling presence, advisory locks)
EVENT_PRESENCE_HEARTBEAT = "presence_heartbeat"
EVENT_PRESENCE_JOINED = "presence_joined"
EVENT_PRESENCE_LEFT = "presence_left"
EVENT_SOFT_LOCK_ACQUIRED = "soft_lock_acquired"
EVENT_SOFT_LOCK_RELEASED = "soft_lock_released"
EVENT_CROSS_DOMAIN_ALERT = "cross_domain_alert"
EVENT_CRDT_OPERATION = "crdt_operation"

CORE_EVENT_TYPES = {
    EVENT_COMMIT_CREATED,
    EVENT_MERGE_CREATED,
    EVENT_CONFLICT_DETECTED,
    EVENT_VERSION_CREATED,
    EVENT_LIFECYCLE_TRANSITION,
    EVENT_PARSE_COMPLETE,
    EVENT_GRAPH_AUTO_LINK_COMPLETE,
    EVENT_SCENE_GRAPH_SNAPSHOT_CREATED,
}

COLLABORATION_EVENT_TYPES = {
    EVENT_PRESENCE_HEARTBEAT,
    EVENT_PRESENCE_JOINED,
    EVENT_PRESENCE_LEFT,
    EVENT_SOFT_LOCK_ACQUIRED,
    EVENT_SOFT_LOCK_RELEASED,
    EVENT_CROSS_DOMAIN_ALERT,
    EVENT_CRDT_OPERATION,
}

ALL_EVENT_TYPES = CORE_EVENT_TYPES | COLLABORATION_EVENT_TYPES


def is_known_event_type(event_type: str) -> bool:
    return event_type in ALL_EVENT_TYPES


def validate_event_type(event_type: str) -> None:
    if not is_known_event_type(event_type):
        raise ValueError(f"unknown_event_type:{event_type}")
