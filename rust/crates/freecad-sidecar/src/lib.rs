use std::sync::{Arc, Mutex};

use hnf_adapter::{HnfDocument, HnfMutation, SceneGraphDeltas, ToolAdapter, ToolArtifact};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sidecar_protocol::{
    method, ApplyMutationsError, ApplyMutationsParams, ApplyMutationsResult, ExportArtifact, ExportParams,
    ExportResult, OkResult, ProjectOpenParams, SceneGraphEdge, SceneGraphNode,
};
use sidecar_runner::{Handler, RunnerConfig, SidecarRunner};
use thiserror::Error;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectContext {
    pub project_id: String,
    pub workspace_root: String,
}

#[derive(Debug, Clone, Default)]
pub struct SidecarState {
    project: Option<ProjectContext>,
}

impl SidecarState {
    pub fn project(&self) -> Option<&ProjectContext> {
        self.project.as_ref()
    }

    pub fn set_project(&mut self, project: ProjectContext) {
        self.project = Some(project);
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MechanicalSolidUpsert {
    pub solid_id: String,
    pub name: String,
    pub material: String,
    pub volume_mm3: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MechanicalConstraintUpsert {
    pub constraint_id: String,
    pub from_solid_id: String,
    pub to_solid_id: String,
    pub constraint_type: String,
}

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum FreecadSidecarError {
    #[error("project is not open")]
    ProjectNotOpen,
    #[error("unsupported mutation kind: {0}")]
    UnsupportedMutation(String),
    #[error("invalid mutation payload: {0}")]
    InvalidPayload(String),
    #[error("adapter error: {0}")]
    Adapter(String),
    #[error("serialization error: {0}")]
    Serialization(String),
}

impl FreecadSidecarError {
    fn as_jsonrpc_error(&self) -> sidecar_protocol::JsonRpcError {
        let code = match self {
            Self::ProjectNotOpen => -32001,
            Self::UnsupportedMutation(_) => -32002,
            Self::InvalidPayload(_) => -32602,
            Self::Adapter(_) | Self::Serialization(_) => -32010,
        };
        sidecar_protocol::JsonRpcError {
            code,
            message: self.to_string(),
            data: None,
        }
    }
}

pub trait FreecadEngineBridge: Send + Sync + 'static {
    fn open_project(&self, _ctx: &ProjectContext) -> Result<(), FreecadSidecarError>;
}

#[derive(Default)]
pub struct NoopFreecadEngineBridge;

impl FreecadEngineBridge for NoopFreecadEngineBridge {
    fn open_project(&self, _ctx: &ProjectContext) -> Result<(), FreecadSidecarError> {
        Ok(())
    }
}

#[derive(Default)]
pub struct MechanicalMutationAdapter;

impl ToolAdapter for MechanicalMutationAdapter {
    type Error = FreecadSidecarError;

    fn apply_mutation(
        &self,
        _document: &mut HnfDocument,
        mutation: &HnfMutation,
    ) -> Result<SceneGraphDeltas, Self::Error> {
        map_mutation_to_deltas(mutation)
    }

    fn export(
        &self,
        _document: &HnfDocument,
        _format: &str,
        _output_dir: &str,
    ) -> Result<Vec<ToolArtifact>, Self::Error> {
        Ok(vec![])
    }
}

pub fn map_mutation_to_deltas(mutation: &HnfMutation) -> Result<SceneGraphDeltas, FreecadSidecarError> {
    let commit_id = mutation
        .payload
        .get("commitId")
        .and_then(Value::as_str)
        .unwrap_or("freecad-local-commit")
        .to_string();

    match mutation.kind.as_str() {
        "mechanical/solid/upsert" => {
            let solid: MechanicalSolidUpsert = serde_json::from_value(mutation.payload.clone())
                .map_err(|err| FreecadSidecarError::InvalidPayload(err.to_string()))?;

            let node = SceneGraphNode {
                nodeId: solid.solid_id.clone(),
                nodeType: "mechanical.solid".to_string(),
                attributes: json!({
                    "name": solid.name,
                    "material": solid.material,
                    "volumeMm3": solid.volume_mm3
                }),
            };

            Ok(SceneGraphDeltas {
                commit_id,
                nodes: vec![node],
                edges: vec![],
            })
        }
        "mechanical/constraint/upsert" => {
            let constraint: MechanicalConstraintUpsert =
                serde_json::from_value(mutation.payload.clone())
                    .map_err(|err| FreecadSidecarError::InvalidPayload(err.to_string()))?;

            let edge = SceneGraphEdge {
                edgeId: constraint.constraint_id,
                fromNodeId: constraint.from_solid_id,
                toNodeId: constraint.to_solid_id,
                edgeType: "mechanical.constraint".to_string(),
                attributes: json!({
                    "constraintType": constraint.constraint_type
                }),
            };

            Ok(SceneGraphDeltas {
                commit_id,
                nodes: vec![],
                edges: vec![edge],
            })
        }
        other => Err(FreecadSidecarError::UnsupportedMutation(other.to_string())),
    }
}

pub fn build_runner(
    config: RunnerConfig,
    state: Arc<Mutex<SidecarState>>,
    adapter: Arc<MechanicalMutationAdapter>,
    engine: Arc<dyn FreecadEngineBridge>,
) -> SidecarRunner {
    let mut runner = SidecarRunner::new(config);

    runner.register_handler(method::PROJECT_OPEN, project_open_handler(state.clone(), engine));
    runner.register_handler(
        method::DOCUMENT_APPLY_MUTATIONS,
        apply_mutations_handler(state.clone(), adapter),
    );
    runner.register_handler(method::DOCUMENT_EXPORT, export_handler(state));
    runner
}

fn project_open_handler(
    state: Arc<Mutex<SidecarState>>,
    engine: Arc<dyn FreecadEngineBridge>,
) -> Handler {
    Arc::new(move |params: Value| {
        let req: ProjectOpenParams =
            serde_json::from_value(params).map_err(|err| FreecadSidecarError::Serialization(err.to_string()).as_jsonrpc_error())?;
        let project = ProjectContext {
            project_id: req.projectId,
            workspace_root: req.workspaceRoot,
        };
        engine
            .open_project(&project)
            .map_err(|err| err.as_jsonrpc_error())?;
        let mut guard = state.lock().map_err(|_| {
            FreecadSidecarError::Adapter("state lock poisoned".to_string()).as_jsonrpc_error()
        })?;
        guard.set_project(project);
        serde_json::to_value(OkResult { ok: true }).map_err(|err| {
            FreecadSidecarError::Serialization(err.to_string()).as_jsonrpc_error()
        })
    })
}

fn apply_mutations_handler(
    state: Arc<Mutex<SidecarState>>,
    adapter: Arc<MechanicalMutationAdapter>,
) -> Handler {
    Arc::new(move |params: Value| {
        let req: ApplyMutationsParams = serde_json::from_value(params)
            .map_err(|err| FreecadSidecarError::Serialization(err.to_string()).as_jsonrpc_error())?;

        let project_is_open = state
            .lock()
            .map_err(|_| FreecadSidecarError::Adapter("state lock poisoned".to_string()).as_jsonrpc_error())?
            .project()
            .is_some();
        if !project_is_open {
            return Err(FreecadSidecarError::ProjectNotOpen.as_jsonrpc_error());
        }

        let mut doc = HnfDocument {
            document_uri: req.documentUri.clone(),
            metadata: json!({}),
            objects: vec![],
        };

        let mut applied = 0usize;
        let mut errors = Vec::new();
        for (idx, mutation) in req.mutations.iter().enumerate() {
            let normalized = HnfMutation {
                kind: mutation.kind.clone(),
                payload: mutation.payload.clone(),
            };
            match adapter.apply_mutation(&mut doc, &normalized) {
                Ok(_deltas) => {
                    applied += 1;
                }
                Err(err) => errors.push(ApplyMutationsError {
                    index: idx,
                    code: "MUTATION_REJECTED".to_string(),
                    message: err.to_string(),
                }),
            }
        }

        serde_json::to_value(ApplyMutationsResult { applied, errors }).map_err(|err| {
            FreecadSidecarError::Serialization(err.to_string()).as_jsonrpc_error()
        })
    })
}

fn export_handler(state: Arc<Mutex<SidecarState>>) -> Handler {
    Arc::new(move |params: Value| {
        let req: ExportParams = serde_json::from_value(params)
            .map_err(|err| FreecadSidecarError::Serialization(err.to_string()).as_jsonrpc_error())?;

        let project_is_open = state
            .lock()
            .map_err(|_| FreecadSidecarError::Adapter("state lock poisoned".to_string()).as_jsonrpc_error())?
            .project()
            .is_some();
        if !project_is_open {
            return Err(FreecadSidecarError::ProjectNotOpen.as_jsonrpc_error());
        }

        let maybe_artifact = if req.format.eq_ignore_ascii_case("step")
            || req.format.eq_ignore_ascii_case("brep")
        {
            vec![ExportArtifact {
                path: format!("{}/{}.{}", req.outputDir, "freecad-export", req.format),
                contentType: "model/step".to_string(),
            }]
        } else {
            vec![]
        };

        serde_json::to_value(ExportResult {
            artifacts: maybe_artifact,
        })
        .map_err(|err| FreecadSidecarError::Serialization(err.to_string()).as_jsonrpc_error())
    })
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use serde_json::json;
    use sidecar_protocol::{Capabilities, JsonRpcResponse};

    use super::*;

    fn test_runner(state: Arc<Mutex<SidecarState>>) -> SidecarRunner {
        build_runner(
            RunnerConfig {
                sidecar_name: "freecad".to_string(),
                sidecar_version: "0.1.0".to_string(),
                capabilities: Capabilities {
                    supportsSceneGraphWrites: Some(true),
                    supportsRoundtripExport: Some(true),
                    extra: BTreeMap::new(),
                },
            },
            state,
            Arc::new(MechanicalMutationAdapter),
            Arc::new(NoopFreecadEngineBridge),
        )
    }

    #[test]
    fn maps_solid_upsert_to_scene_graph_node() {
        let mutation = HnfMutation {
            kind: "mechanical/solid/upsert".to_string(),
            payload: json!({
                "commitId": "c-1",
                "solid_id": "solid-123",
                "name": "Base Plate",
                "material": "Aluminum",
                "volume_mm3": 12345.0
            }),
        };

        let deltas = map_mutation_to_deltas(&mutation).expect("must map");
        assert_eq!(deltas.commit_id, "c-1");
        assert_eq!(deltas.nodes.len(), 1);
        assert_eq!(deltas.nodes[0].nodeType, "mechanical.solid");
        assert_eq!(deltas.edges.len(), 0);
    }

    #[test]
    fn maps_constraint_upsert_to_scene_graph_edge() {
        let mutation = HnfMutation {
            kind: "mechanical/constraint/upsert".to_string(),
            payload: json!({
                "commitId": "c-2",
                "constraint_id": "constraint-456",
                "from_solid_id": "solid-A",
                "to_solid_id": "solid-B",
                "constraint_type": "mate"
            }),
        };

        let deltas = map_mutation_to_deltas(&mutation).expect("must map");
        assert_eq!(deltas.commit_id, "c-2");
        assert_eq!(deltas.edges.len(), 1);
        assert_eq!(deltas.edges[0].edgeType, "mechanical.constraint");
        assert_eq!(deltas.nodes.len(), 0);
    }

    #[test]
    fn apply_mutations_requires_open_project() {
        let state = Arc::new(Mutex::new(SidecarState::default()));
        let runner = test_runner(state);
        let request = json!({
            "jsonrpc": "2.0",
            "id": 11,
            "method": "hcp/document/applyMutations",
            "params": {
                "documentUri": "hcp://project/doc.FCStd",
                "mutations": []
            }
        })
        .to_string();

        let line = runner
            .handle_request_line(&request)
            .expect("runner response")
            .expect("jsonrpc response");
        let response: JsonRpcResponse = serde_json::from_str(&line).expect("response parses");
        assert!(response.error.is_some());
        assert!(response
            .error
            .expect("jsonrpc error")
            .message
            .contains("project is not open"));
    }

    #[test]
    fn handler_flow_opens_project_applies_and_exports() {
        let state = Arc::new(Mutex::new(SidecarState::default()));
        let runner = test_runner(state);

        let open = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "hcp/project/open",
            "params": {
                "projectId": "proj-1",
                "workspaceRoot": "/tmp/workspace",
                "auth": {"apiUrl":"https://api.hcp.local","token":"secret"}
            }
        })
        .to_string();
        let apply = json!({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "hcp/document/applyMutations",
            "params": {
                "documentUri": "hcp://project/doc.FCStd",
                "mutations": [
                    {
                        "kind": "mechanical/solid/upsert",
                        "payload": {
                            "commitId": "c-9",
                            "solid_id": "solid-1",
                            "name": "Bracket",
                            "material": "Steel",
                            "volume_mm3": 88.0
                        }
                    },
                    {
                        "kind": "mechanical/unknown",
                        "payload": {}
                    }
                ]
            }
        })
        .to_string();
        let export = json!({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "hcp/document/export",
            "params": {
                "documentUri": "hcp://project/doc.FCStd",
                "format": "step",
                "outputDir": "/tmp/out"
            }
        })
        .to_string();

        let open_resp = runner
            .handle_request_line(&open)
            .expect("open response")
            .expect("open line");
        let apply_resp = runner
            .handle_request_line(&apply)
            .expect("apply response")
            .expect("apply line");
        let export_resp = runner
            .handle_request_line(&export)
            .expect("export response")
            .expect("export line");

        let open_json: JsonRpcResponse = serde_json::from_str(&open_resp).expect("open parses");
        let apply_json: JsonRpcResponse = serde_json::from_str(&apply_resp).expect("apply parses");
        let export_json: JsonRpcResponse =
            serde_json::from_str(&export_resp).expect("export parses");
        let apply_result = apply_json.result.expect("apply result");
        let export_result = export_json.result.expect("export result");

        assert_eq!(open_json.result.expect("result")["ok"], true);
        assert_eq!(apply_result["applied"], 1);
        assert_eq!(apply_result["errors"][0]["code"], "MUTATION_REJECTED");
        assert_eq!(export_result["artifacts"][0]["contentType"], "model/step");
    }
}
