use std::sync::{Arc, Mutex};

use serde_json::{json, Value};
use sidecar_protocol::{
    method, ApplyMutationsError, ApplyMutationsParams, ApplyMutationsResult, ExportParams, ExportResult,
    JsonRpcError, Mutation, OkResult, ProjectOpenParams, SceneGraphEdge, SceneGraphNode,
    SceneGraphUpsertEdgesParams, SceneGraphUpsertNodesParams,
};
use sidecar_runner::{Handler, SidecarRunner};
use thiserror::Error;

#[derive(Debug, Clone, PartialEq)]
pub struct ProjectContext {
    pub project_id: String,
    pub workspace_root: String,
    pub api_url: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SceneDelta {
    pub nodes: Vec<SceneGraphNode>,
    pub edges: Vec<SceneGraphEdge>,
}

#[derive(Debug, Error)]
pub enum SidecarError {
    #[error("project is not open")]
    ProjectNotOpen,
    #[error("kicad bridge error: {0}")]
    Bridge(String),
    #[error("scene graph error: {0}")]
    SceneGraph(String),
}

pub trait KiCadBridge: Send + Sync {
    fn apply_mutation(
        &self,
        ctx: &ProjectContext,
        document_uri: &str,
        index: usize,
        mutation: &Mutation,
    ) -> Result<SceneDelta, SidecarError>;

    fn export(
        &self,
        ctx: &ProjectContext,
        document_uri: &str,
        format: &str,
        output_dir: &str,
    ) -> Result<ExportResult, SidecarError>;
}

pub trait SceneGraphClient: Send + Sync {
    fn upsert_nodes(&self, params: SceneGraphUpsertNodesParams) -> Result<(), SidecarError>;
    fn upsert_edges(&self, params: SceneGraphUpsertEdgesParams) -> Result<(), SidecarError>;
}

pub struct SubprocessKiCadBridge;

impl KiCadBridge for SubprocessKiCadBridge {
    fn apply_mutation(
        &self,
        _ctx: &ProjectContext,
        document_uri: &str,
        index: usize,
        mutation: &Mutation,
    ) -> Result<SceneDelta, SidecarError> {
        let node_kind = map_mutation_kind_to_node_type(&mutation.kind);
        let node_id = format!("{document_uri}:{index}:{node_kind}");
        let node = SceneGraphNode {
            nodeId: node_id.clone(),
            nodeType: node_kind.to_string(),
            attributes: json!({
                "mutationKind": mutation.kind,
                "payload": mutation.payload,
                "adapter": "subprocess-stub"
            }),
        };
        let edge = SceneGraphEdge {
            edgeId: format!("edge:{node_id}"),
            fromNodeId: document_uri.to_string(),
            toNodeId: node_id,
            edgeType: "derived_from".to_string(),
            attributes: json!({}),
        };
        Ok(SceneDelta {
            nodes: vec![node],
            edges: vec![edge],
        })
    }

    fn export(
        &self,
        _ctx: &ProjectContext,
        document_uri: &str,
        format: &str,
        output_dir: &str,
    ) -> Result<ExportResult, SidecarError> {
        let artifact_path = format!(
            "{output_dir}/{}.{format}",
            document_uri.replace("://", "_").replace('/', "_")
        );
        Ok(ExportResult {
            artifacts: vec![sidecar_protocol::ExportArtifact {
                path: artifact_path,
                contentType: format!("application/{format}"),
            }],
        })
    }
}

#[derive(Clone)]
pub struct KiCadSidecar {
    bridge: Arc<dyn KiCadBridge>,
    scene_graph: Arc<dyn SceneGraphClient>,
    state: Arc<Mutex<Option<ProjectContext>>>,
}

impl KiCadSidecar {
    pub fn new(bridge: Arc<dyn KiCadBridge>, scene_graph: Arc<dyn SceneGraphClient>) -> Self {
        Self {
            bridge,
            scene_graph,
            state: Arc::new(Mutex::new(None)),
        }
    }

    pub fn register_handlers(&self, runner: &mut SidecarRunner) {
        runner.register_handler(method::PROJECT_OPEN, self.project_open_handler());
        runner.register_handler(
            method::DOCUMENT_APPLY_MUTATIONS,
            self.apply_mutations_handler(),
        );
        runner.register_handler(method::DOCUMENT_EXPORT, self.export_handler());
    }

    fn project_open_handler(&self) -> Handler {
        let state = Arc::clone(&self.state);
        Arc::new(move |params: Value| {
            let parsed: ProjectOpenParams =
                serde_json::from_value(params).map_err(invalid_params_error)?;
            let ctx = ProjectContext {
                project_id: parsed.projectId,
                workspace_root: parsed.workspaceRoot,
                api_url: parsed.auth.apiUrl,
            };
            let mut guard = state.lock().expect("project state lock");
            *guard = Some(ctx);
            Ok(serde_json::to_value(OkResult { ok: true }).expect("serialize ok result"))
        })
    }

    fn apply_mutations_handler(&self) -> Handler {
        let sidecar = self.clone();
        Arc::new(move |params: Value| {
            let parsed: ApplyMutationsParams =
                serde_json::from_value(params).map_err(invalid_params_error)?;
            let commit_id = new_commit_id();
            let result = sidecar.apply_and_upsert(&commit_id, &parsed);
            serde_json::to_value(result).map_err(internal_error)
        })
    }

    fn export_handler(&self) -> Handler {
        let sidecar = self.clone();
        Arc::new(move |params: Value| {
            let parsed: ExportParams =
                serde_json::from_value(params).map_err(invalid_params_error)?;
            let result = sidecar.export_document(&parsed).map_err(to_jsonrpc_error)?;
            serde_json::to_value(result).map_err(internal_error)
        })
    }

    fn export_document(&self, params: &ExportParams) -> Result<ExportResult, SidecarError> {
        let ctx = self.require_context()?;
        self.bridge
            .export(&ctx, &params.documentUri, &params.format, &params.outputDir)
    }

    fn apply_and_upsert(
        &self,
        commit_id: &str,
        params: &ApplyMutationsParams,
    ) -> ApplyMutationsResult {
        let mut errors = Vec::new();
        let mut applied = 0usize;
        let ctx = match self.require_context() {
            Ok(v) => v,
            Err(err) => {
                return ApplyMutationsResult {
                    applied,
                    errors: vec![ApplyMutationsError {
                        index: 0,
                        code: "project_not_open".to_string(),
                        message: err.to_string(),
                    }],
                }
            }
        };

        for (index, mutation) in params.mutations.iter().enumerate() {
            match self
                .bridge
                .apply_mutation(&ctx, &params.documentUri, index, mutation)
            {
                Ok(delta) => {
                    let node_params = SceneGraphUpsertNodesParams {
                        commitId: commit_id.to_string(),
                        nodes: delta.nodes,
                    };
                    let edge_params = SceneGraphUpsertEdgesParams {
                        commitId: commit_id.to_string(),
                        edges: delta.edges,
                    };
                    let upsert = self
                        .scene_graph
                        .upsert_nodes(node_params)
                        .and_then(|_| self.scene_graph.upsert_edges(edge_params));
                    match upsert {
                        Ok(()) => applied += 1,
                        Err(err) => errors.push(ApplyMutationsError {
                            index,
                            code: "scene_graph_upsert_failed".to_string(),
                            message: err.to_string(),
                        }),
                    }
                }
                Err(err) => errors.push(ApplyMutationsError {
                    index,
                    code: "mutation_apply_failed".to_string(),
                    message: err.to_string(),
                }),
            }
        }

        ApplyMutationsResult { applied, errors }
    }

    fn require_context(&self) -> Result<ProjectContext, SidecarError> {
        let guard = self.state.lock().expect("project state lock");
        guard.clone().ok_or(SidecarError::ProjectNotOpen)
    }
}

fn invalid_params_error(err: serde_json::Error) -> JsonRpcError {
    JsonRpcError {
        code: -32602,
        message: "Invalid params".to_string(),
        data: Some(json!({ "detail": err.to_string() })),
    }
}

fn internal_error(err: serde_json::Error) -> JsonRpcError {
    JsonRpcError {
        code: -32603,
        message: "Internal error".to_string(),
        data: Some(json!({ "detail": err.to_string() })),
    }
}

fn to_jsonrpc_error(err: SidecarError) -> JsonRpcError {
    JsonRpcError {
        code: -32010,
        message: err.to_string(),
        data: None,
    }
}

fn map_mutation_kind_to_node_type(kind: &str) -> &'static str {
    if kind.starts_with("schematic.") {
        "kicad.schematic.element"
    } else if kind.starts_with("pcb.") {
        "kicad.pcb.element"
    } else {
        "kicad.generic.mutation"
    }
}

fn new_commit_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock after epoch");
    format!("kicad-{}", now.as_nanos())
}

#[cfg(test)]
mod tests {
    use super::*;
    use sidecar_protocol::Capabilities;
    use sidecar_protocol::method;
    use sidecar_runner::{RunnerConfig, SidecarRunner};
    use std::collections::BTreeMap;

    #[derive(Default)]
    struct FakeSceneGraph {
        nodes_calls: Mutex<Vec<SceneGraphUpsertNodesParams>>,
        edges_calls: Mutex<Vec<SceneGraphUpsertEdgesParams>>,
    }

    impl SceneGraphClient for FakeSceneGraph {
        fn upsert_nodes(&self, params: SceneGraphUpsertNodesParams) -> Result<(), SidecarError> {
            self.nodes_calls.lock().expect("nodes lock").push(params);
            Ok(())
        }

        fn upsert_edges(&self, params: SceneGraphUpsertEdgesParams) -> Result<(), SidecarError> {
            self.edges_calls.lock().expect("edges lock").push(params);
            Ok(())
        }
    }

    fn new_runner() -> SidecarRunner {
        SidecarRunner::new(RunnerConfig {
            sidecar_name: "kicad".to_string(),
            sidecar_version: "0.1.0".to_string(),
            capabilities: Capabilities {
                supportsSceneGraphWrites: Some(true),
                supportsRoundtripExport: Some(true),
                extra: BTreeMap::new(),
            },
        })
    }

    #[test]
    fn handler_requires_project_open_before_mutations() {
        let scene = Arc::new(FakeSceneGraph::default());
        let sidecar = KiCadSidecar::new(Arc::new(SubprocessKiCadBridge), scene);
        let mut runner = new_runner();
        sidecar.register_handlers(&mut runner);

        let req = json!({
            "jsonrpc":"2.0",
            "id": 1,
            "method": method::DOCUMENT_APPLY_MUTATIONS,
            "params": {
                "documentUri":"hcp://doc/a",
                "mutations":[{"kind":"schematic.symbol.upsert","payload":{"ref":"R1"}}]
            }
        });
        let out = runner
            .handle_request_line(&req.to_string())
            .expect("runner output")
            .expect("has response");
        let parsed: sidecar_protocol::JsonRpcResponse =
            serde_json::from_str(&out).expect("parse json-rpc response");
        let result = parsed.result.expect("result present");
        assert_eq!(result["applied"], 0);
        assert_eq!(result["errors"][0]["code"], "project_not_open");
    }

    #[test]
    fn handlers_apply_mutations_and_emit_scene_upserts() {
        let scene = Arc::new(FakeSceneGraph::default());
        let sidecar = KiCadSidecar::new(Arc::new(SubprocessKiCadBridge), scene.clone());
        let mut runner = new_runner();
        sidecar.register_handlers(&mut runner);

        let open_req = json!({
            "jsonrpc":"2.0",
            "id": 1,
            "method": method::PROJECT_OPEN,
            "params": {
                "projectId":"p1",
                "workspaceRoot":"/tmp/work",
                "auth":{"apiUrl":"https://api.hcp.local","token":"redacted"}
            }
        });
        runner
            .handle_request_line(&open_req.to_string())
            .expect("open response");

        let mutate_req = json!({
            "jsonrpc":"2.0",
            "id": 2,
            "method": method::DOCUMENT_APPLY_MUTATIONS,
            "params": {
                "documentUri":"hcp://doc/board",
                "mutations":[
                    {"kind":"schematic.symbol.upsert","payload":{"ref":"R1"}},
                    {"kind":"pcb.track.upsert","payload":{"net":"GND"}}
                ]
            }
        });
        let out = runner
            .handle_request_line(&mutate_req.to_string())
            .expect("runner output")
            .expect("has response");
        let parsed: sidecar_protocol::JsonRpcResponse =
            serde_json::from_str(&out).expect("parse response");
        let result = parsed.result.expect("result present");
        assert_eq!(result["applied"], 2);
        assert_eq!(result["errors"], json!([]));

        let nodes = scene.nodes_calls.lock().expect("nodes calls");
        let edges = scene.edges_calls.lock().expect("edges calls");
        assert_eq!(nodes.len(), 2);
        assert_eq!(edges.len(), 2);
        assert_eq!(nodes[0].nodes[0].nodeType, "kicad.schematic.element");
        assert_eq!(nodes[1].nodes[0].nodeType, "kicad.pcb.element");
    }

    #[test]
    fn export_handler_returns_best_effort_artifact() {
        let scene = Arc::new(FakeSceneGraph::default());
        let sidecar = KiCadSidecar::new(Arc::new(SubprocessKiCadBridge), scene);
        let mut runner = new_runner();
        sidecar.register_handlers(&mut runner);

        let open_req = json!({
            "jsonrpc":"2.0",
            "id": 1,
            "method": method::PROJECT_OPEN,
            "params": {
                "projectId":"p1",
                "workspaceRoot":"/tmp/work",
                "auth":{"apiUrl":"https://api.hcp.local","token":"redacted"}
            }
        });
        runner
            .handle_request_line(&open_req.to_string())
            .expect("open response");

        let export_req = json!({
            "jsonrpc":"2.0",
            "id": 3,
            "method": method::DOCUMENT_EXPORT,
            "params": {
                "documentUri":"hcp://doc/board",
                "format":"step",
                "outputDir":"/tmp/out"
            }
        });
        let out = runner
            .handle_request_line(&export_req.to_string())
            .expect("runner output")
            .expect("has response");
        let parsed: sidecar_protocol::JsonRpcResponse =
            serde_json::from_str(&out).expect("parse response");
        let result = parsed.result.expect("result present");
        assert_eq!(result["artifacts"][0]["contentType"], "application/step");
    }
}
use std::sync::{Arc, Mutex};

use hnf_adapter::SceneGraphDeltas;
use serde_json::{json, Value};
use sidecar_protocol::{
    method, ApplyMutationsError, ApplyMutationsParams, ApplyMutationsResult, ExportArtifact,
    ExportParams, ExportResult, JsonRpcError, Mutation, OkResult, ProjectOpenParams,
    SceneGraphEdge, SceneGraphNode, SceneGraphUpsertEdgesParams, SceneGraphUpsertNodesParams,
    SceneGraphUpsertResult,
};
use sidecar_runner::SidecarRunner;
use thiserror::Error;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectContext {
    pub project_id: String,
    pub workspace_root: String,
    pub api_url: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct MutationOutcome {
    pub scene_deltas: SceneGraphDeltas,
}

pub trait KiCadBinding: Send + Sync {
    fn apply_mutation(
        &self,
        project: &ProjectContext,
        document_uri: &str,
        mutation: &Mutation,
    ) -> Result<MutationOutcome, SidecarError>;

    fn export(
        &self,
        project: &ProjectContext,
        document_uri: &str,
        format: &str,
        output_dir: &str,
    ) -> Result<Vec<ExportArtifact>, SidecarError>;
}

pub trait SceneGraphClient: Send + Sync {
    fn upsert_nodes(
        &self,
        params: SceneGraphUpsertNodesParams,
    ) -> Result<SceneGraphUpsertResult, SidecarError>;
    fn upsert_edges(
        &self,
        params: SceneGraphUpsertEdgesParams,
    ) -> Result<SceneGraphUpsertResult, SidecarError>;
}

#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum SidecarError {
    #[error("project not opened")]
    ProjectNotOpen,
    #[error("binding error: {0}")]
    Binding(String),
    #[error("scene graph error: {0}")]
    SceneGraph(String),
}

#[derive(Default)]
struct State {
    project: Option<ProjectContext>,
}

pub struct KiCadSidecar<B: KiCadBinding, S: SceneGraphClient> {
    binding: B,
    scene_graph: S,
    state: Mutex<State>,
}

impl<B: KiCadBinding, S: SceneGraphClient> KiCadSidecar<B, S> {
    pub fn new(binding: B, scene_graph: S) -> Self {
        Self {
            binding,
            scene_graph,
            state: Mutex::new(State::default()),
        }
    }

    pub fn register_handlers(self: &Arc<Self>, runner: &mut SidecarRunner) {
        let sidecar = Arc::clone(self);
        runner.register_handler(
            method::PROJECT_OPEN,
            Arc::new(move |params| sidecar.handle_project_open_json(params)),
        );

        let sidecar = Arc::clone(self);
        runner.register_handler(
            method::DOCUMENT_APPLY_MUTATIONS,
            Arc::new(move |params| sidecar.handle_apply_mutations_json(params)),
        );

        let sidecar = Arc::clone(self);
        runner.register_handler(
            method::DOCUMENT_EXPORT,
            Arc::new(move |params| sidecar.handle_export_json(params)),
        );
    }

    pub fn handle_project_open(&self, params: ProjectOpenParams) -> Result<OkResult, SidecarError> {
        let mut state = self.state.lock().expect("state mutex poisoned");
        state.project = Some(ProjectContext {
            project_id: params.projectId,
            workspace_root: params.workspaceRoot,
            api_url: params.auth.apiUrl,
        });
        Ok(OkResult { ok: true })
    }

    pub fn handle_apply_mutations(
        &self,
        params: ApplyMutationsParams,
    ) -> Result<ApplyMutationsResult, SidecarError> {
        let project = self.current_project()?;
        let mut applied = 0usize;
        let mut errors = Vec::new();

        for (index, mutation) in params.mutations.iter().enumerate() {
            match self
                .binding
                .apply_mutation(&project, &params.documentUri, mutation)
            {
                Ok(outcome) => {
                    self.emit_scene_graph_upserts(outcome.scene_deltas)?;
                    applied += 1;
                }
                Err(err) => errors.push(ApplyMutationsError {
                    index,
                    code: "KICAD_MUTATION_FAILED".to_string(),
                    message: err.to_string(),
                }),
            }
        }

        Ok(ApplyMutationsResult { applied, errors })
    }

    pub fn handle_export(&self, params: ExportParams) -> Result<ExportResult, SidecarError> {
        let project = self.current_project()?;
        // Best-effort export in Phase 0.5: return empty artifacts if export is unavailable.
        let artifacts = self
            .binding
            .export(
                &project,
                &params.documentUri,
                &params.format,
                &params.outputDir,
            )
            .unwrap_or_default();
        Ok(ExportResult { artifacts })
    }

    fn emit_scene_graph_upserts(&self, deltas: SceneGraphDeltas) -> Result<(), SidecarError> {
        if !deltas.nodes.is_empty() {
            self.scene_graph.upsert_nodes(SceneGraphUpsertNodesParams {
                commitId: deltas.commit_id.clone(),
                nodes: deltas.nodes,
            })?;
        }

        if !deltas.edges.is_empty() {
            self.scene_graph.upsert_edges(SceneGraphUpsertEdgesParams {
                commitId: deltas.commit_id,
                edges: deltas.edges,
            })?;
        }

        Ok(())
    }

    fn current_project(&self) -> Result<ProjectContext, SidecarError> {
        self.state
            .lock()
            .expect("state mutex poisoned")
            .project
            .clone()
            .ok_or(SidecarError::ProjectNotOpen)
    }

    fn handle_project_open_json(&self, params: Value) -> Result<Value, JsonRpcError> {
        let parsed = parse_params::<ProjectOpenParams>(params)?;
        self.handle_project_open(parsed)
            .map(|v| serde_json::to_value(v).expect("project open result serializes"))
            .map_err(error_to_jsonrpc)
    }

    fn handle_apply_mutations_json(&self, params: Value) -> Result<Value, JsonRpcError> {
        let parsed = parse_params::<ApplyMutationsParams>(params)?;
        self.handle_apply_mutations(parsed)
            .map(|v| serde_json::to_value(v).expect("apply result serializes"))
            .map_err(error_to_jsonrpc)
    }

    fn handle_export_json(&self, params: Value) -> Result<Value, JsonRpcError> {
        let parsed = parse_params::<ExportParams>(params)?;
        self.handle_export(parsed)
            .map(|v| serde_json::to_value(v).expect("export result serializes"))
            .map_err(error_to_jsonrpc)
    }
}

pub fn map_mutation_to_scene_delta(document_uri: &str, index: usize, mutation: &Mutation) -> SceneGraphDeltas {
    let safe_kind = mutation.kind.replace('/', ".").replace(' ', "_");
    let commit_id = format!("{}:{}", document_uri, index);
    let node_id = format!("node:{}:{}", safe_kind, index);
    let edge_id = format!("edge:{}:{}", safe_kind, index);

    SceneGraphDeltas {
        commit_id,
        nodes: vec![SceneGraphNode {
            nodeId: node_id.clone(),
            nodeType: "kicad.mutation".to_string(),
            attributes: json!({
                "kind": mutation.kind,
                "payload": mutation.payload,
                "index": index
            }),
        }],
        edges: vec![SceneGraphEdge {
            edgeId: edge_id,
            fromNodeId: format!("doc:{}", document_uri),
            toNodeId: node_id,
            edgeType: "applies_mutation".to_string(),
            attributes: json!({
                "kind": mutation.kind
            }),
        }],
    }
}

fn parse_params<T: serde::de::DeserializeOwned>(params: Value) -> Result<T, JsonRpcError> {
    serde_json::from_value(params).map_err(|err| JsonRpcError {
        code: -32602,
        message: format!("Invalid params: {err}"),
        data: None,
    })
}

fn error_to_jsonrpc(err: SidecarError) -> JsonRpcError {
    JsonRpcError {
        code: -32000,
        message: err.to_string(),
        data: None,
    }
}

pub struct StubKiCadBinding;

impl KiCadBinding for StubKiCadBinding {
    fn apply_mutation(
        &self,
        _project: &ProjectContext,
        document_uri: &str,
        mutation: &Mutation,
    ) -> Result<MutationOutcome, SidecarError> {
        Ok(MutationOutcome {
            scene_deltas: map_mutation_to_scene_delta(document_uri, 0, mutation),
        })
    }

    fn export(
        &self,
        _project: &ProjectContext,
        _document_uri: &str,
        format: &str,
        output_dir: &str,
    ) -> Result<Vec<ExportArtifact>, SidecarError> {
        let content_type = match format {
            "step" => "model/step",
            "svg" => "image/svg+xml",
            _ => return Err(SidecarError::Binding("unsupported export format".to_string())),
        };

        Ok(vec![ExportArtifact {
            path: format!("{output_dir}/kicad-export.{format}"),
            contentType: content_type.to_string(),
        }])
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Mutex;

    use serde_json::json;
    use sidecar_protocol::{ApplyMutationsParams, Mutation, ProjectAuth, ProjectOpenParams};

    use super::*;

    #[derive(Default)]
    struct FakeBinding {
        fail_kind: Option<String>,
    }

    impl KiCadBinding for FakeBinding {
        fn apply_mutation(
            &self,
            _project: &ProjectContext,
            document_uri: &str,
            mutation: &Mutation,
        ) -> Result<MutationOutcome, SidecarError> {
            if self.fail_kind.as_deref() == Some(&mutation.kind) {
                return Err(SidecarError::Binding("synthetic apply failure".to_string()));
            }
            Ok(MutationOutcome {
                scene_deltas: map_mutation_to_scene_delta(document_uri, 1, mutation),
            })
        }

        fn export(
            &self,
            _project: &ProjectContext,
            _document_uri: &str,
            _format: &str,
            _output_dir: &str,
        ) -> Result<Vec<ExportArtifact>, SidecarError> {
            Err(SidecarError::Binding("export unavailable".to_string()))
        }
    }

    #[derive(Default)]
    struct RecordingSceneGraph {
        nodes: Mutex<Vec<SceneGraphUpsertNodesParams>>,
        edges: Mutex<Vec<SceneGraphUpsertEdgesParams>>,
    }

    impl SceneGraphClient for RecordingSceneGraph {
        fn upsert_nodes(
            &self,
            params: SceneGraphUpsertNodesParams,
        ) -> Result<SceneGraphUpsertResult, SidecarError> {
            let count = params.nodes.len();
            self.nodes.lock().expect("nodes lock").push(params);
            Ok(SceneGraphUpsertResult {
                upserted: count,
            })
        }

        fn upsert_edges(
            &self,
            params: SceneGraphUpsertEdgesParams,
        ) -> Result<SceneGraphUpsertResult, SidecarError> {
            let count = params.edges.len();
            self.edges.lock().expect("edges lock").push(params);
            Ok(SceneGraphUpsertResult {
                upserted: count,
            })
        }
    }

    fn opened_sidecar(binding: FakeBinding, scene_graph: RecordingSceneGraph) -> KiCadSidecar<FakeBinding, RecordingSceneGraph> {
        let sidecar = KiCadSidecar::new(binding, scene_graph);
        sidecar
            .handle_project_open(ProjectOpenParams {
                projectId: "proj-1".to_string(),
                workspaceRoot: "/tmp/proj".to_string(),
                auth: ProjectAuth {
                    apiUrl: "https://api.example".to_string(),
                    token: "redacted".to_string(),
                },
            })
            .expect("open project");
        sidecar
    }

    #[test]
    fn project_open_initializes_state() {
        let sidecar = KiCadSidecar::new(FakeBinding::default(), RecordingSceneGraph::default());
        let result = sidecar
            .handle_project_open(ProjectOpenParams {
                projectId: "proj-2".to_string(),
                workspaceRoot: "/tmp/work".to_string(),
                auth: ProjectAuth {
                    apiUrl: "https://api.example".to_string(),
                    token: "secret".to_string(),
                },
            })
            .expect("project open");
        assert!(result.ok);
        assert_eq!(
            sidecar.current_project().expect("project context").workspace_root,
            "/tmp/work"
        );
    }

    #[test]
    fn apply_mutations_emits_scene_graph_upserts() {
        let sidecar = opened_sidecar(FakeBinding::default(), RecordingSceneGraph::default());
        let result = sidecar
            .handle_apply_mutations(ApplyMutationsParams {
                documentUri: "hcp://doc/board.kicad_pcb".to_string(),
                mutations: vec![Mutation {
                    kind: "pcb.addTrack".to_string(),
                    payload: json!({"net":"VCC"}),
                }],
            })
            .expect("apply mutations");

        assert_eq!(result.applied, 1);
        assert!(result.errors.is_empty());
        assert_eq!(
            sidecar
                .scene_graph
                .nodes
                .lock()
                .expect("node log")
                .len(),
            1
        );
        assert_eq!(
            sidecar
                .scene_graph
                .edges
                .lock()
                .expect("edge log")
                .len(),
            1
        );
    }

    #[test]
    fn apply_mutations_reports_binding_failures() {
        let binding = FakeBinding {
            fail_kind: Some("schematic.addSymbol".to_string()),
        };
        let sidecar = opened_sidecar(binding, RecordingSceneGraph::default());
        let result = sidecar
            .handle_apply_mutations(ApplyMutationsParams {
                documentUri: "hcp://doc/schematic.kicad_sch".to_string(),
                mutations: vec![
                    Mutation {
                        kind: "schematic.addSymbol".to_string(),
                        payload: json!({"refdes":"R1"}),
                    },
                    Mutation {
                        kind: "pcb.addTrack".to_string(),
                        payload: json!({}),
                    },
                ],
            })
            .expect("apply mutations");

        assert_eq!(result.applied, 1);
        assert_eq!(result.errors.len(), 1);
        assert_eq!(result.errors[0].index, 0);
    }

    #[test]
    fn export_is_best_effort_when_unavailable() {
        let sidecar = opened_sidecar(FakeBinding::default(), RecordingSceneGraph::default());
        let result = sidecar
            .handle_export(ExportParams {
                documentUri: "hcp://doc/board.kicad_pcb".to_string(),
                format: "step".to_string(),
                outputDir: "/tmp/out".to_string(),
            })
            .expect("export handler");
        assert!(result.artifacts.is_empty());
    }

    #[test]
    fn mutation_mapping_produces_stable_scene_delta() {
        let mutation = Mutation {
            kind: "schematic.addSymbol".to_string(),
            payload: json!({"refdes":"R1"}),
        };

        let delta = map_mutation_to_scene_delta("hcp://doc/schematic.kicad_sch", 3, &mutation);
        assert_eq!(delta.commit_id, "hcp://doc/schematic.kicad_sch:3");
        assert_eq!(delta.nodes[0].nodeType, "kicad.mutation");
        assert_eq!(delta.edges[0].edgeType, "applies_mutation");
        assert_eq!(delta.nodes[0].attributes["kind"], "schematic.addSymbol");
    }
}
