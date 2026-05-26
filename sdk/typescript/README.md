# @hcp/sdk

TypeScript SDK for Hardware Cloud Platform. Node.js 18+.

## Install

```bash
cd sdk/typescript && npm install && npm run build
```

## Quickstart

```typescript
import { Client } from "@hcp/sdk";

const client = new Client({
  apiKey: process.env.HCP_API_KEY,
  apiUrl: "http://localhost:8000",
});

const project = await client.projects.create("Flight Controller Rev C");
const upload = await client.objects.upload({
  filePath: "./board.kicad_pcb",
  projectId: project.id,
  name: "main-board",
  waitForParse: true,
});

const bom = await client.bom.get(upload.object.id);
const deps = await client.graph.dependencies(upload.object.id, 2);
const hits = await client.search.query({ q: "STM32", type: "PCB" });
```

## Tests

```bash
npm test
```

Coverage threshold: 80%.
