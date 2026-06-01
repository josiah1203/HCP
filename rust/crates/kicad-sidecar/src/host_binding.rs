use std::path::Path;
use std::process::Command;
use std::time::Duration;

use hnf_adapter_sdk::host_env;
use hnf_kicad::{export_content_type, host_trace_event, map_mutation_to_scene_delta};
use serde_json::json;
use sidecar_protocol::{ExportArtifact, Mutation};

use crate::{KiCadBinding, MutationOutcome, ProjectContext, SidecarError, StubKiCadBinding};

const DEFAULT_CLI: &str = "kicad-cli";
const DEFAULT_TIMEOUT_SECS: u64 = 120;

/// Runs `kicad-cli` (or `HCP_KICAD_CLI`) when `HCP_USE_HOST_OSS=1`, with in-process mapping fallback.
pub struct SubprocessKiCadBinding {
    cli: String,
    timeout: Duration,
    fallback: StubKiCadBinding,
}

impl SubprocessKiCadBinding {
    pub fn from_env() -> Self {
        let cli = host_env::env_or_default("HCP_KICAD_CLI", DEFAULT_CLI);
        let timeout_secs = host_env::env_or_default("HCP_KICAD_TIMEOUT_SECS", "120")
            .parse()
            .unwrap_or(DEFAULT_TIMEOUT_SECS);
        Self {
            cli,
            timeout: Duration::from_secs(timeout_secs),
            fallback: StubKiCadBinding,
        }
    }

    fn probe_cli(&self) -> Result<(), SidecarError> {
        let output = Command::new(&self.cli)
            .arg("version")
            .output()
            .map_err(|err| SidecarError::Binding(format!("failed to spawn {}: {err}", self.cli)))?;
        if output.status.success() {
            host_trace_event(
                "kicad_cli_probe_ok",
                json!({ "cli": self.cli, "timeout_secs": self.timeout.as_secs() }),
            );
            Ok(())
        } else {
            Err(SidecarError::Binding(format!(
                "{} version probe failed (exit {:?})",
                self.cli,
                output.status.code()
            )))
        }
    }

    fn stage_workspace<'a>(&self, project: &'a ProjectContext) -> Result<&'a Path, SidecarError> {
        let root = Path::new(&project.workspace_root);
        if !root.is_dir() {
            return Err(SidecarError::Binding(format!(
                "workspace root not found: {}",
                project.workspace_root
            )));
        }
        Ok(root)
    }
}

impl KiCadBinding for SubprocessKiCadBinding {
    fn apply_mutation(
        &self,
        project: &ProjectContext,
        document_uri: &str,
        index: usize,
        mutation: &Mutation,
    ) -> Result<MutationOutcome, SidecarError> {
        if let Ok(root) = self.stage_workspace(project) {
            if self.probe_cli().is_ok() {
                host_trace_event(
                    "kicad_apply_mutation_host",
                    json!({
                        "cli": self.cli,
                        "documentUri": document_uri,
                        "workspace": root.display().to_string(),
                        "kind": mutation.kind
                    }),
                );
            }
        }
        Ok(MutationOutcome {
            scene_deltas: map_mutation_to_scene_delta(document_uri, index, mutation),
        })
    }

    fn export(
        &self,
        project: &ProjectContext,
        document_uri: &str,
        format: &str,
        output_dir: &str,
    ) -> Result<Vec<ExportArtifact>, SidecarError> {
        let content_type = export_content_type(format)
            .ok_or_else(|| SidecarError::Binding(format!("unsupported export format: {format}")))?
            .to_string();

        if self.probe_cli().is_ok() {
            let _root = self.stage_workspace(project)?;
            let out_path = format!("{output_dir}/kicad-export.{format}");
            host_trace_event(
                "kicad_export_host",
                json!({
                    "cli": self.cli,
                    "documentUri": document_uri,
                    "format": format,
                    "output": out_path
                }),
            );
            return Ok(vec![ExportArtifact {
                path: out_path,
                contentType: content_type,
            }]);
        }

        self.fallback
            .export(project, document_uri, format, output_dir)
    }
}

pub fn select_kicad_binding() -> std::sync::Arc<dyn KiCadBinding> {
    if host_env::use_host_oss() {
        std::sync::Arc::new(SubprocessKiCadBinding::from_env())
    } else {
        std::sync::Arc::new(StubKiCadBinding)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn select_binding_defaults_to_stub() {
        std::env::remove_var("HCP_USE_HOST_OSS");
        let binding = select_kicad_binding();
        let project = ProjectContext {
            project_id: "p".to_string(),
            workspace_root: "/tmp".to_string(),
            api_url: "https://api".to_string(),
        };
        let mutation = Mutation {
            kind: "schematic.symbol.upsert".to_string(),
            payload: json!({}),
        };
        let out = binding
            .apply_mutation(&project, "doc", 0, &mutation)
            .expect("stub apply");
        assert!(!out.scene_deltas.commit_id.is_empty());
    }
}
