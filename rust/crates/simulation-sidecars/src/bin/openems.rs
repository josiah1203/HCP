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
    let result = run_engine_payload(SimulationEngine::OpenEms, &payload, SystemSubprocessRunner)?;
    println!("{}", serde_json::to_string(&result)?);
    Ok(())
}
