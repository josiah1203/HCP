# Upload to HCP — GitHub Action

Upload hardware artifacts to Hardware Cloud Platform on release (§16.3).

## Usage

```yaml
- uses: ./actions/hcp-upload
  with:
    api_key: ${{ secrets.HCP_API_KEY }}
    project_id: ${{ vars.HCP_PROJECT_ID }}
    files: 'build/**/*'
    wait_for_parse: 'true'
    api_url: 'https://api.hcp.io'
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `api_key` | yes | — | HCP API key |
| `project_id` | yes | — | HCP project ID |
| `files` | no | `build/**/*` | Glob for files to upload |
| `wait_for_parse` | no | `true` | Poll until parse completes |
| `api_url` | no | `https://api.hcp.io` | API base URL |

## Outputs

| Output | Description |
|--------|-------------|
| `object_ids` | Comma-separated object IDs |
| `version_ids` | Comma-separated version IDs |

## Build action bundle

```bash
cd actions/hcp-upload
npm install
npm run package
```

Commit `dist/index.js` for `action.yml` `main: dist/index.js`.
