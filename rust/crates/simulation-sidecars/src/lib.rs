use std::collections::BTreeMap;
use std::process::Command;
use std::sync::Arc;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sidecar_protocol::{
    ApplyMutationsError, ApplyMutationsParams, ApplyMutationsResult, ExportArtifact, ExportParams,
    ExportResult, JsonRpcError,
};
use sidecar_runner::{Handler, SidecarRunner};
use thiserror::Error;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SimulationEngine {
    Ngspice,
    #[serde(rename = "openems")]
    OpenEms,
    Elmer,
}

impl SimulationEngine {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Ngspice => "ngspice",
            Self::OpenEms => "openems",
            Self::Elmer => "elmer",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SimulationConfig {
    pub engine: SimulationEngine,
    pub job_id: String,
    #[serde(default)]
    pub output_dir: Option<String>,
    #[serde(default)]
    pub solver_input: Value,
    #[serde(default)]
    pub command: Option<Vec<String>>,
    #[serde(default)]
    pub expected_artifacts: Vec<ExpectedArtifact>,
}

impl SimulationConfig {
    pub fn from_mutation_payload(payload: &Value) -> Result<Self, SimulationAdapterError> {
        if let Some(simulation) = payload.get("simulation") {
            return Ok(serde_json::from_value(simulation.clone())?);
        }
        Ok(serde_json::from_value(payload.clone())?)
    }

    pub fn from_export_payload(
        payload: &Value,
        output_dir: impl Into<String>,
    ) -> Result<Self, SimulationAdapterError> {
        let mut cfg = Self::from_mutation_payload(payload)?;
        cfg.output_dir = Some(output_dir.into());
        Ok(cfg)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ExpectedArtifact {
    pub path: String,
    pub content_type: String,
    pub role: String,
    #[serde(default)]
    pub render_hint: Option<String>,
    #[serde(default)]
    pub size_bytes: Option<u64>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct CommandSpec {
    pub program: String,
    pub args: Vec<String>,
    pub cwd: Option<String>,
    pub env: BTreeMap<String, String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct CommandOutcome {
    pub exit_code: i32,
    pub stdout: String,
    pub stderr: String,
}

pub trait SubprocessRunner {
    fn run(&self, spec: &CommandSpec) -> Result<CommandOutcome, SimulationAdapterError>;
}

#[derive(Debug, Default, Clone)]
pub struct SystemSubprocessRunner;

impl SubprocessRunner for SystemSubprocessRunner {
    fn run(&self, spec: &CommandSpec) -> Result<CommandOutcome, SimulationAdapterError> {
        let mut command = Command::new(&spec.program);
        command.args(&spec.args);
        if let Some(cwd) = &spec.cwd {
            command.current_dir(cwd);
        }
        if !spec.env.is_empty() {
            command.envs(&spec.env);
        }
        let output = command.output()?;
        Ok(CommandOutcome {
            exit_code: output.status.code().unwrap_or(-1),
            stdout: String::from_utf8_lossy(&output.stdout).to_string(),
            stderr: String::from_utf8_lossy(&output.stderr).to_string(),
        })
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct NormalizedResultEnvelope {
    pub engine: String,
    pub job_id: String,
    pub status: String,
    pub exit_code: i32,
    pub artifacts: Vec<ArtifactMetadata>,
    pub stdout: String,
    pub stderr: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ArtifactMetadata {
    pub path: String,
    pub content_type: String,
    pub role: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub render_hint: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub size_bytes: Option<u64>,
}

pub struct SimulationJobAdapter<R: SubprocessRunner> {
    engine: SimulationEngine,
    runner: R,
}

impl<R: SubprocessRunner> SimulationJobAdapter<R> {
    pub fn new(engine: SimulationEngine, runner: R) -> Self {
        Self { engine, runner }
    }

    pub fn run_from_mutation_payload(
        &self,
        payload: &Value,
    ) -> Result<NormalizedResultEnvelope, SimulationAdapterError> {
        let config = SimulationConfig::from_mutation_payload(payload)?;
        self.run_config(config)
    }

    pub fn run_from_export_payload(
        &self,
        payload: &Value,
        output_dir: impl Into<String>,
    ) -> Result<NormalizedResultEnvelope, SimulationAdapterError> {
        let config = SimulationConfig::from_export_payload(payload, output_dir)?;
        self.run_config(config)
    }

    pub fn run_config(
        &self,
        config: SimulationConfig,
    ) -> Result<NormalizedResultEnvelope, SimulationAdapterError> {
        if config.engine != self.engine {
            return Err(SimulationAdapterError::EngineMismatch {
                adapter: self.engine.as_str().to_string(),
                config: config.engine.as_str().to_string(),
            });
        }

        let spec = build_command_spec(&config)?;
        let outcome = self.runner.run(&spec)?;
        Ok(map_outcome(config, outcome))
    }

    pub fn run_apply_mutations(
        &self,
        params: &ApplyMutationsParams,
    ) -> Result<Vec<NormalizedResultEnvelope>, SimulationAdapterError> {
        let mut envelopes = Vec::new();
        for mutation in &params.mutations {
            envelopes.push(self.run_from_mutation_payload(&mutation.payload)?);
        }
        Ok(envelopes)
    }

    pub fn run_export(
        &self,
        params: &ExportParams,
        payload: &Value,
    ) -> Result<NormalizedResultEnvelope, SimulationAdapterError> {
        self.run_from_export_payload(payload, params.outputDir.clone())
    }
}

pub fn register_protocol_handlers<R>(
    runner: &mut SidecarRunner,
    engine: SimulationEngine,
    adapter: Arc<SimulationJobAdapter<R>>,
) where
    R: SubprocessRunner + Send + Sync + 'static,
{
    let apply_adapter = adapter.clone();
    let apply_handler: Handler = Arc::new(move |params| {
        let parsed: ApplyMutationsParams = serde_json::from_value(params).map_err(jsonrpc_invalid_params)?;
        let mut errors = Vec::new();
        let mut applied = 0usize;

        for (index, mutation) in parsed.mutations.iter().enumerate() {
            match apply_adapter.run_from_mutation_payload(&mutation.payload) {
                Ok(_) => applied += 1,
                Err(err) => errors.push(ApplyMutationsError {
                    index,
                    code: "SIMULATION_RUN_FAILED".to_string(),
                    message: err.to_string(),
                }),
            }
        }

        let result = ApplyMutationsResult { applied, errors };
        serde_json::to_value(result).map_err(jsonrpc_internal_error)
    });
    runner.register_handler(format!("simulation/{}/applyMutations", engine.as_str()), apply_handler);

    let export_adapter = adapter.clone();
    let export_handler: Handler = Arc::new(move |params| {
        #[derive(Deserialize)]
        struct ExportWithPayload {
            #[serde(flatten)]
            export: ExportParams,
            payload: Value,
        }
        let parsed: ExportWithPayload =
            serde_json::from_value(params).map_err(jsonrpc_invalid_params)?;
        let normalized = export_adapter
            .run_export(&parsed.export, &parsed.payload)
            .map_err(jsonrpc_exec_error)?;
        let artifacts = normalized
            .artifacts
            .into_iter()
            .map(|artifact| ExportArtifact {
                path: artifact.path,
                contentType: artifact.content_type,
            })
            .collect();
        let result = ExportResult { artifacts };
        serde_json::to_value(result).map_err(jsonrpc_internal_error)
    });
    runner.register_handler(format!("simulation/{}/export", engine.as_str()), export_handler);
}

fn which_on_path(program: &str) -> Option<String> {
    let path_var = std::env::var_os("PATH")?;
    std::env::split_paths(&path_var)
        .map(|dir| dir.join(program))
        .find(|candidate| candidate.is_file())
        .map(|p| p.to_string_lossy().into_owned())
}

fn host_default_command(engine: SimulationEngine) -> Option<(String, Vec<String>)> {
    if !hnf_adapter_sdk::host_env::sim_use_host() {
        return None;
    }
    let program = match engine {
        SimulationEngine::Ngspice => "ngspice",
        SimulationEngine::OpenEms => "openems",
        SimulationEngine::Elmer => "ElmerSolver",
    };
    which_on_path(program).map(|path| (path, vec!["-v".to_string()]))
}

pub fn build_command_spec(config: &SimulationConfig) -> Result<CommandSpec, SimulationAdapterError> {
    let (program, args) = match &config.command {
        Some(cmd) if !cmd.is_empty() => (cmd[0].clone(), cmd[1..].to_vec()),
        Some(_) => return Err(SimulationAdapterError::InvalidCommand),
        None => {
            if let Some(host) = host_default_command(config.engine) {
                host
            } else {
                default_stub_command(config.engine, &config.job_id)
            }
        }
    };

    let mut env = BTreeMap::new();
    env.insert("HCP_SIM_ENGINE".to_string(), config.engine.as_str().to_string());
    env.insert("HCP_SIM_JOB_ID".to_string(), config.job_id.clone());

    Ok(CommandSpec {
        program,
        args,
        cwd: config.output_dir.clone(),
        env,
    })
}

fn default_stub_command(engine: SimulationEngine, job_id: &str) -> (String, Vec<String>) {
    (
        "sh".to_string(),
        vec![
            "-lc".to_string(),
            format!("printf 'stub-run {} {}\\n'", engine.as_str(), job_id),
        ],
    )
}

fn map_outcome(config: SimulationConfig, outcome: CommandOutcome) -> NormalizedResultEnvelope {
    let artifacts = if config.expected_artifacts.is_empty() {
        let base = config
            .output_dir
            .unwrap_or_else(|| ".".to_string())
            .trim_end_matches('/')
            .to_string();
        vec![ArtifactMetadata {
            path: format!("{base}/{}-{}.json", config.engine.as_str(), config.job_id),
            content_type: "application/json".to_string(),
            role: "result-manifest".to_string(),
            render_hint: Some("host-renderable".to_string()),
            size_bytes: None,
        }]
    } else {
        config
            .expected_artifacts
            .into_iter()
            .map(|artifact| ArtifactMetadata {
                path: artifact.path,
                content_type: artifact.content_type,
                role: artifact.role,
                render_hint: artifact.render_hint,
                size_bytes: artifact.size_bytes,
            })
            .collect()
    };

    NormalizedResultEnvelope {
        engine: config.engine.as_str().to_string(),
        job_id: config.job_id,
        status: if outcome.exit_code == 0 {
            "succeeded".to_string()
        } else {
            "failed".to_string()
        },
        exit_code: outcome.exit_code,
        artifacts,
        stdout: outcome.stdout,
        stderr: outcome.stderr,
    }
}

#[derive(Debug, Error)]
pub enum SimulationAdapterError {
    #[error("invalid simulation config: {0}")]
    InvalidConfig(#[from] serde_json::Error),
    #[error("subprocess execution failed: {0}")]
    Subprocess(#[from] std::io::Error),
    #[error("command override cannot be empty")]
    InvalidCommand,
    #[error("engine mismatch: adapter={adapter}, config={config}")]
    EngineMismatch { adapter: String, config: String },
}

fn jsonrpc_invalid_params(err: serde_json::Error) -> JsonRpcError {
    JsonRpcError {
        code: -32602,
        message: format!("Invalid params: {err}"),
        data: None,
    }
}

fn jsonrpc_internal_error(err: serde_json::Error) -> JsonRpcError {
    JsonRpcError {
        code: -32603,
        message: format!("Internal error: {err}"),
        data: None,
    }
}

fn jsonrpc_exec_error(err: SimulationAdapterError) -> JsonRpcError {
    JsonRpcError {
        code: -32000,
        message: err.to_string(),
        data: None,
    }
}

pub fn run_engine_payload<R: SubprocessRunner>(
    engine: SimulationEngine,
    payload: &Value,
    runner: R,
) -> Result<NormalizedResultEnvelope, SimulationAdapterError> {
    SimulationJobAdapter::new(engine, runner).run_from_mutation_payload(payload)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[derive(Clone)]
    struct MockRunner {
        outcome: CommandOutcome,
    }

    impl SubprocessRunner for MockRunner {
        fn run(&self, _spec: &CommandSpec) -> Result<CommandOutcome, SimulationAdapterError> {
            Ok(self.outcome.clone())
        }
    }

    #[test]
    fn parses_nested_mutation_payload_config() {
        let payload = json!({
            "simulation": {
                "engine": "ngspice",
                "job_id": "job-001",
                "solver_input": {"netlist": "R1 1 0 1k"},
                "expected_artifacts": [{
                    "path": "/tmp/run.ac.raw",
                    "content_type": "application/octet-stream",
                    "role": "raw-waveform",
                    "render_hint": "waveform"
                }]
            }
        });

        let cfg = SimulationConfig::from_mutation_payload(&payload).expect("parse simulation cfg");
        assert_eq!(cfg.engine, SimulationEngine::Ngspice);
        assert_eq!(cfg.job_id, "job-001");
        assert_eq!(cfg.expected_artifacts.len(), 1);
    }

    #[test]
    fn export_payload_overrides_output_dir() {
        let payload = json!({
            "engine": "openems",
            "job_id": "job-010"
        });

        let cfg =
            SimulationConfig::from_export_payload(&payload, "/tmp/exports").expect("parse export cfg");
        assert_eq!(cfg.engine, SimulationEngine::OpenEms);
        assert_eq!(cfg.output_dir.as_deref(), Some("/tmp/exports"));
    }

    #[test]
    fn maps_success_outcome_to_normalized_envelope() {
        let payload = json!({
            "engine": "elmer",
            "job_id": "job-500",
            "output_dir": "/tmp/elmer"
        });

        let adapter = SimulationJobAdapter::new(
            SimulationEngine::Elmer,
            MockRunner {
                outcome: CommandOutcome {
                    exit_code: 0,
                    stdout: "ok".to_string(),
                    stderr: "".to_string(),
                },
            },
        );
        let result = adapter
            .run_from_mutation_payload(&payload)
            .expect("run and normalize");

        assert_eq!(result.status, "succeeded");
        assert_eq!(result.engine, "elmer");
        assert_eq!(result.artifacts[0].role, "result-manifest");
        assert!(result.artifacts[0].path.ends_with("/elmer-job-500.json"));
    }

    #[test]
    fn maps_failure_outcome_to_normalized_envelope() {
        let payload = json!({
            "engine": "ngspice",
            "job_id": "job-900",
            "expected_artifacts": [{
                "path": "/tmp/out.log",
                "content_type": "text/plain",
                "role": "solver-log"
            }]
        });

        let adapter = SimulationJobAdapter::new(
            SimulationEngine::Ngspice,
            MockRunner {
                outcome: CommandOutcome {
                    exit_code: 2,
                    stdout: "".to_string(),
                    stderr: "failed".to_string(),
                },
            },
        );
        let result = adapter
            .run_from_mutation_payload(&payload)
            .expect("run and normalize");

        assert_eq!(result.status, "failed");
        assert_eq!(result.exit_code, 2);
        assert_eq!(result.artifacts[0].role, "solver-log");
    }

    #[test]
    fn host_command_uses_stub_when_flag_off() {
        std::env::remove_var("HCP_SIM_USE_HOST");
        let payload = json!({
            "engine": "ngspice",
            "job_id": "job-host-off"
        });
        let cfg = SimulationConfig::from_mutation_payload(&payload).expect("cfg");
        let spec = build_command_spec(&cfg).expect("spec");
        assert_eq!(spec.program, "sh");
    }

    #[test]
    fn apply_mutations_flow_parses_protocol_payload() {
        let params = ApplyMutationsParams {
            documentUri: "hcp://docs/sim".to_string(),
            mutations: vec![sidecar_protocol::Mutation {
                kind: "simulation.run".to_string(),
                payload: json!({
                    "engine": "ngspice",
                    "job_id": "job-apply"
                }),
            }],
        };

        let adapter = SimulationJobAdapter::new(
            SimulationEngine::Ngspice,
            MockRunner {
                outcome: CommandOutcome {
                    exit_code: 0,
                    stdout: "done".to_string(),
                    stderr: "".to_string(),
                },
            },
        );
        let envelopes = adapter
            .run_apply_mutations(&params)
            .expect("parse and execute mutation flow");
        assert_eq!(envelopes.len(), 1);
        assert_eq!(envelopes[0].job_id, "job-apply");
    }
}
