export const HCP_RPC_PROTOCOL_V0 = "hcp.rpc.v0" as const;

export type JsonRpcId = string | number | null;

export type JsonRpcRequest<TParams> = {
  jsonrpc: "2.0";
  id: JsonRpcId;
  method: string;
  params: TParams;
};

export type JsonRpcNotification<TParams> = {
  jsonrpc: "2.0";
  method: string;
  params: TParams;
};

export type JsonRpcError = {
  code: number;
  message: string;
  data?: unknown;
};

export type JsonRpcResponse<TResult> =
  | { jsonrpc: "2.0"; id: JsonRpcId; result: TResult }
  | { jsonrpc: "2.0"; id: JsonRpcId; error: JsonRpcError };

export type HcpPingParams = Record<string, never>;
export type HcpPingResult = {
  protocol: typeof HCP_RPC_PROTOCOL_V0;
  sidecar: { name: string; version: string };
  capabilities: {
    supportsSceneGraphWrites?: boolean;
    supportsRoundtripExport?: boolean;
    [k: string]: unknown;
  };
};

export type ProjectOpenParams = {
  projectId: string;
  workspaceRoot: string;
  auth: { apiUrl: string; token: string };
};
export type OkResult = { ok: true };

export type ApplyMutationsParams = {
  documentUri: string;
  mutations: Array<{ kind: string; payload: Record<string, unknown> }>;
};
export type ApplyMutationsResult = {
  applied: number;
  errors: Array<{ index: number; code: string; message: string }>;
};

export type ExportParams = {
  documentUri: string;
  format: string;
  outputDir: string;
};
export type ExportResult = {
  artifacts: Array<{ path: string; contentType: string }>;
};

export type SceneGraphNode = {
  nodeId: string;
  nodeType: string;
  attributes: Record<string, unknown>;
};

export type SceneGraphEdge = {
  edgeId: string;
  fromNodeId: string;
  toNodeId: string;
  edgeType: string;
  attributes: Record<string, unknown>;
};

export type SceneGraphUpsertNodesParams = { commitId: string; nodes: SceneGraphNode[] };
export type SceneGraphUpsertEdgesParams = { commitId: string; edges: SceneGraphEdge[] };
export type SceneGraphUpsertResult = { upserted: number };

export type SceneGraphCreateSnapshotParams = {
  commitId: string;
  snapshotFormat: "json" | "glb" | "octree+json";
};
export type SceneGraphCreateSnapshotResult = {
  snapshotId: string;
  artifactObjectId: string;
  artifactVersionNum: number;
};

