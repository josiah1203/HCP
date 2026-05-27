# Fork integration contracts (v0)

This directory defines the **stable integration seam** for:

- IDE **extension host** ⇄ tool **sidecars** (KiCad/FreeCAD)
- Sidecars ⇄ **Scene Graph service**
- Sidecars/extension host ⇄ **HOS** (version control + object store + events)

The initial contract is **JSON-RPC 2.0 over stdio** (preferred for sidecars) plus a small set of **HTTP** endpoints for HOS server operations (until a JSON-RPC gateway is introduced).

## Versioning

- Protocol version: `hcp.rpc.v0`
- Backwards compatibility policy: additive only within `v0` (new methods/fields allowed; breaking changes require `v1`)

## Transports

- **Extension host ⇄ sidecar**: JSON-RPC 2.0 over stdio.
- **Sidecar ⇄ scene graph**: JSON-RPC 2.0 over stdio or TCP (same message shapes).
- **Sidecar/extension host ⇄ HOS**: HTTP(S) `v1` REST for now (client surface is stable; transport can be swapped later).

## Schemas

- `jsonrpc/hcp-ide-sidecar.v0.json`: Extension host ⇄ sidecar RPC methods.
- `jsonrpc/hcp-sidecar-scenegraph.v0.json`: Sidecar ⇄ scene graph RPC methods.
- `jsonrpc/hcp-hos-client.v0.json`: Language-agnostic HOS client surface (method names + request/response shapes).

## Types

- `typescript/`: TypeScript types that shims/webviews can import/copy.
- `python/`: Python dataclasses/TypedDicts used by the reference client.

## Regression harness

The regression harness skeleton lives in:

- `../regression/README.md`

