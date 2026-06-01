use std::io::{self, Read};

use serde_json::Value;
use simulation_sidecars::{run_engine_payload, SimulationEngine, SystemSubprocessRunner};

fn main() {
    if let Err(err) = run() {
        eprintln!("{err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let payload: Value = serde_json::from_str(&input)?;
    let result = run_engine_payload(SimulationEngine::Elmer, &payload, SystemSubprocessRunner)?;
    println!("{}", serde_json::to_string(&result)?);
    Ok(())
}
use std::sync::Arc;

use serde_json::Value;
use sidecar_protocol::method;
use sidecar_runner::{RunnerConfig, SidecarRunner};
use simulation_sidecars::{
    handle_apply_mutations, handle_export, parse_export_payload, SimulationEngine,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    run_sidecar("elmer", SimulationEngine::Elmer)
}

fn run_sidecar(name: &str, engine: SimulationEngine) -> Result<(), Box<dyn std::error::Error>> {
    let mut runner = SidecarRunner::new(RunnerConfig {
        sidecar_name: name.to_string(),
        sidecar_version: env!("CARGO_PKG_VERSION").to_string(),
        capabilities: sidecar_protocol::Capabilities {
            supportsSceneGraphWrites: Some(false),
            supportsRoundtripExport: Some(true),
            extra: Default::default(),
        },
    });

    runner.register_handler(
        method::DOCUMENT_APPLY_MUTATIONS,
        Arc::new(move |params: Value| {
            let parsed: sidecar_protocol::ApplyMutationsParams =
                serde_json::from_value(params).map_err(|err| sidecar_protocol::JsonRpcError {
                    code: -32602,
                    message: format!("Invalid params: {err}"),
                    data: None,
                })?;
            handle_apply_mutations(parsed, engine)
        }),
    );

    runner.register_handler(
        method::DOCUMENT_EXPORT,
        Arc::new(move |params: Value| {
            let parsed = parse_export_payload(params)?;
            Ok(handle_export(parsed))
        }),
    );

    let stdin = std::io::stdin();
    let mut reader = std::io::BufReader::new(stdin.lock());
    let stdout = std::io::stdout();
    let mut writer = stdout.lock();
    runner.run_stdio(&mut reader, &mut writer)?;
    Ok(())
}
