use std::process::Command;

use hnf_adapter_sdk::host_env;
use hnf_freecad::host_trace_event;
use serde_json::json;

use crate::{FreecadEngineBridge, FreecadSidecarError, ProjectContext};

const DEFAULT_CMD: &str = "freecadcmd";

/// Launches `freecadcmd` (or `HCP_FREECAD_CMD`) for project open when `HCP_USE_HOST_OSS=1`.
pub struct SubprocessFreecadEngineBridge {
    cmd: String,
}

impl SubprocessFreecadEngineBridge {
    pub fn from_env() -> Self {
        Self {
            cmd: host_env::env_or_default("HCP_FREECAD_CMD", DEFAULT_CMD),
        }
    }

    fn probe(&self) -> Result<(), FreecadSidecarError> {
        let output = Command::new(&self.cmd)
            .arg("--version")
            .output()
            .map_err(|err| {
                FreecadSidecarError::Adapter(format!("failed to spawn {}: {err}", self.cmd))
            })?;
        if output.status.success() {
            host_trace_event(
                "freecadcmd_probe_ok",
                json!({ "cmd": self.cmd }),
            );
            Ok(())
        } else {
            Err(FreecadSidecarError::Adapter(format!(
                "{} --version failed (exit {:?})",
                self.cmd,
                output.status.code()
            )))
        }
    }
}

impl FreecadEngineBridge for SubprocessFreecadEngineBridge {
    fn open_project(&self, ctx: &ProjectContext) -> Result<(), FreecadSidecarError> {
        self.probe()?;
        host_trace_event(
            "freecad_open_project",
            json!({
                "cmd": self.cmd,
                "projectId": ctx.project_id,
                "workspaceRoot": ctx.workspace_root
            }),
        );
        Ok(())
    }
}

pub fn select_engine_bridge() -> std::sync::Arc<dyn FreecadEngineBridge> {
    if host_env::use_host_oss() {
        std::sync::Arc::new(SubprocessFreecadEngineBridge::from_env())
    } else {
        std::sync::Arc::new(crate::NoopFreecadEngineBridge)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn select_bridge_defaults_to_noop() {
        std::env::remove_var("HCP_USE_HOST_OSS");
        let bridge = select_engine_bridge();
        let ctx = ProjectContext {
            project_id: "p".to_string(),
            workspace_root: "/tmp".to_string(),
        };
        assert!(bridge.open_project(&ctx).is_ok());
    }
}
