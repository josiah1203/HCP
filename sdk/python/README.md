# hcp-sdk

Python SDK for [Hardware Cloud Platform](https://github.com/hcp/hcp).

## Install

```bash
pip install -e "sdk/python[dev]"
```

## Quickstart

```python
import hcp

client = hcp.Client(
    api_key="hcp_live_...",
    api_url="http://localhost:8000",
)

project = client.projects.create(name="Flight Controller Rev C")
result = client.objects.upload(
    file_path="./board.kicad_pcb",
    project_id=str(project["id"]),
    name="main-board",
    wait_for_parse=True,
    parse_timeout=120,
)

bom = client.bom.get(object_id=str(result["object"]["id"]))
deps = client.graph.dependencies(object_id=str(result["object"]["id"]), depth=2)
hits = client.search.query(q="STM32", type="PCB")

client.close()
```

## Tests

```bash
cd sdk/python && pip install -e ".[dev]" && pytest
```

Coverage target: 80%+.
