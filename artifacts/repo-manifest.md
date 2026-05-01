# Repository Manifest

## elastic/docs-content

- Default branch: `main`
- License file: `LICENSE`

### Top-level directories
- `.github`
- `.vscode`
- `cloud-account`
- `contribute-docs`
- `deploy-manage`
- `explore-analyze`
- `extend`
- `get-started`
- `manage-data`
- `raw-migrated-files`
- `reference`
- `release-notes`
- `serverless`
- `solutions`
- `troubleshoot`

### Key config files
- `.gitignore`

### Project files
- `README.md`
- `.github/CODEOWNERS`

### Workflows
- `.github/workflows/add-new-team-label.yml`
- `.github/workflows/add-to-board.yml`
- `.github/workflows/co-docs-builder.yml`
- `.github/workflows/comment-on-asciidoc-changes.yml`
- `.github/workflows/docs-ai-menu.yml`
- `.github/workflows/docs-build.yml`
- `.github/workflows/docs-deploy.yml`
- `.github/workflows/docs-issue-scope.yml`
- `.github/workflows/docs-pr-ai-menu.yml`
- `.github/workflows/docs-preview-cleanup.yml`
- `.github/workflows/docs-triage.yml`
- `.github/workflows/label-community-issues.yml`
- `.github/workflows/sync-sheets-keyless.yml`
- `.github/workflows/update-kube-stack-version.yml`

## elastic/docs-builder

- Default branch: `main`
- License file: `LICENSE.txt`

### Top-level directories
- `.claude`
- `.github`
- `.husky`
- `.vscode`
- `actions`
- `aspire`
- `build`
- `config`
- `docs`
- `src`
- `tests`
- `tests-integration`

### Key config files
- `.editorconfig`
- `.gitignore`
- `package-lock.json`

### Project files
- `README.md`
- `actions/update-link-index/README.md`
- `aspire/README.md`
- `src/Elastic.Documentation.LegacyDocs/README.md`
- `src/Elastic.Documentation.Navigation/README.md`
- `src/infra/docs-lambda-changelog-scrubber/README.md`
- `src/infra/docs-lambda-index-publisher/README.md`
- `CONTRIBUTING.md`
- `.github/CODEOWNERS`

### Workflows
- `.github/workflows/assembler-preview-cleanup.yml`
- `.github/workflows/assembler-preview.yml`
- `.github/workflows/auto-add-needs-triage-label.yml`
- `.github/workflows/build-changelog-scrubber-lambda.yml`
- `.github/workflows/build-link-index-updater-lambda.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/comment-on-asciidoc-changes.yml`
- `.github/workflows/create-major-tag.yml`
- `.github/workflows/detect-duplicate-issues.yml`
- `.github/workflows/docs-preview-cleanup-local.yml`
- `.github/workflows/docs-preview-local.yml`
- `.github/workflows/license.yml`
- `.github/workflows/prerelease.yml`
- `.github/workflows/release-drafter.yml`
- `.github/workflows/release.yml`
- `.github/workflows/required-labels.yml`
- `.github/workflows/smoke-test.yml`
- `.github/workflows/updatecli.yml`

## elastic/docs

- Default branch: `master`
- License file: `none found`

### Top-level directories
- `.buildkite`
- `.bundle`
- `.ci`
- `.docker`
- `.github`
- `.repos`
- `air_gapped`
- `extra`
- `integtest`
- `lib`
- `preview`
- `resources`
- `shared`
- `template`

### Key config files
- `.gitignore`
- `Dockerfile`
- `Makefile`
- `package.json`
- `yarn.lock`

### Project files
- `.docker/README`
- `.github/actions/docs-preview/README.md`
- `README.asciidoc`
- `extra/README`
- `integtest/README`
- `resources/asciidoctor/README`
- `shared/versions/stack/README`
- `.github/CODEOWNERS`

### Workflows
- `.github/workflows/doc-preview.yml`
- `.github/workflows/patch-release-version-bump.yml`

## elastic/elasticsearch-labs

- Default branch: `main`
- License file: `LICENSE`

### Top-level directories
- `.github`
- `bin`
- `datasets`
- `docker`
- `example-apps`
- `img`
- `k8s`
- `notebooks`
- `supporting-blog-content`
- `supporting-video-content`
- `telemetry`

### Key config files
- `.gitignore`
- `.pre-commit-config.yaml`
- `Makefile`

### Project files
- `README.md`
- `docker/README.md`
- `example-apps/README.md`
- `example-apps/chatbot-rag-app/README.md`
- `example-apps/elasticsearch-mcp-server/README.md`
- `example-apps/internal-knowledge-search/README.md`
- `example-apps/openai-embeddings/README.md`
- `example-apps/relevance-workbench/README.md`
- `example-apps/search-tutorial/README.md`
- `example-apps/search-tutorial/start/search-tutorial/README.md`
- `example-apps/search-tutorial/v1/search-tutorial/README.md`
- `example-apps/search-tutorial/v2/search-tutorial/README.md`
- `example-apps/search-tutorial/v3/search-tutorial/README.md`
- `example-apps/workplace-search/README.md`
- `k8s/README.md`
- `notebooks/README.md`
- `notebooks/generative-ai/README.md`
- `notebooks/integrations/README.md`
- `notebooks/integrations/aryn/README.md`
- `notebooks/integrations/hugging-face/README.md`
- `notebooks/integrations/llama-index/README.md`
- `notebooks/integrations/llama3/README.md`
- `notebooks/integrations/openai/README.md`
- `notebooks/search/README.md`
- `supporting-blog-content/ElasticDocs_GPT/README.md`
- `supporting-blog-content/ElasticGPT_Plugin/README.md`
- `supporting-blog-content/README.md`
- `supporting-blog-content/add-ai-generated-summaries/app-search-reference-ui-react-master/README.md`
- `supporting-blog-content/agent-builder-a2a-agent-framework/README.md`
- `supporting-blog-content/agent-builder-a2a-strands-agents/README.md`
- `supporting-blog-content/building-a-recipe-search-with-elasticsearch/README.md`
- `supporting-blog-content/building-actionable-ai-automating-it-requests-with-agent-builder-and-one-workflow/README.md`
- `supporting-blog-content/building-advanced-visualizations-kibana-vega/README.md`
- `supporting-blog-content/building-elasticsearch-apis-with-fastapi-websockets/README.md`
- `supporting-blog-content/building-multimodal-rag-with-elasticsearch-gotham/README.md`
- `supporting-blog-content/customer-success-example/README.md`
- `supporting-blog-content/elasticsearch-inference-api-and-hugging-face/README.md`
- `supporting-blog-content/elasticsearch-through-apache-kafka/README.md`
- `supporting-blog-content/elasticsearch-typescript-claude-mcp/README.md`
- `supporting-blog-content/elasticsearch_llm_cache/README.md`
- `supporting-blog-content/esql-millionaire/README.md`
- `supporting-blog-content/esre-with-blazor/elastic-blazor/README.md`
- `supporting-blog-content/fetch-surrounding-chunks/README.md`
- `supporting-blog-content/geospatial-data-ingest/README.md`
- `supporting-blog-content/geospatial-data-ingest/airports/README.md`
- `supporting-blog-content/geospatial-data-ingest/drone/README.md`
- `supporting-blog-content/github-assistant/README.md`
- `supporting-blog-content/homecraft-vertex/README.md`
- `supporting-blog-content/how-and-why-bbq/README.md`
- `supporting-blog-content/human-in-the-loop-with-langgraph-and-elasticsearch/README.md`
- `supporting-blog-content/hybrid-search-for-an-e-commerce-product-catalogue/README.md`
- `supporting-blog-content/hybrid-search-for-an-e-commerce-product-catalogue/app-product-store/README.md`
- `supporting-blog-content/hybrid-search-for-an-e-commerce-product-catalogue/product-store-search/README.md`
- `supporting-blog-content/langgraph-js-elasticsearch/README.md`
- `supporting-blog-content/langraph-retrieval-agent-template-demo/README.md`
- `supporting-blog-content/local-rag-with-lightweight-elasticsearch/README.md`
- `supporting-blog-content/music-search/README.md`
- `supporting-blog-content/navigating-an-elastic-vector-database/README.md`
- `supporting-blog-content/self-querying-retrieval/README.md`
- `supporting-blog-content/unifying-elastic-vector-database-and-llms-for-intelligent-query/README.md`
- `supporting-blog-content/using-openelm-models/OpenELM/README.md`
- `supporting-blog-content/using-ragas-with-elasticsearch/README.md`
- `supporting-blog-content/you-know-for-context/README.md`
- `CONTRIBUTING.md`
- `CODEOWNERS`

### Workflows
- `.github/workflows/docker-chatbot-rag-app.yml`
- `.github/workflows/pre-commit.yml`
- `.github/workflows/tests.yml`

## elastic/labs-releases

- Default branch: `main`
- License file: `LICENSE.md`

### Top-level directories
- `extractors`
- `indicators`
- `tools`

### Key config files
- `.gitignore`

### Project files
- `README.md`
- `extractors/README.md`
- `extractors/lobshot/README.md`
- `extractors/redlinestealer/README.md`
- `extractors/remcos/README.md`
- `indicators/README.md`
- `indicators/app-bound_bypass/README.md`
- `indicators/banshee/README.md`
- `indicators/bitsloth/README.md`
- `indicators/blister/README.md`
- `indicators/confused_rat/README.md`
- `indicators/ghostengine/README.md`
- `indicators/ghostpulse/README.md`
- `indicators/grimresource/README.md`
- `indicators/guloader/README.md`
- `indicators/jokerspy/README.md`
- `indicators/lobshot/README.md`
- `indicators/outlaw/README.md`
- `indicators/pikabot/README.md`
- `indicators/r77/README.md`
- `indicators/ref0657/README.md`
- `indicators/ref5961/README.md`
- `indicators/ref6138/README.md`
- `indicators/ref7001/README.md`
- `indicators/rustbucket/README.md`
- `indicators/shelby-strategy/README.md`
- `indicators/shellter/README.md`
- `indicators/spectralviper/README.md`
- `indicators/tollbooth/README.md`
- `indicators/warmcookie/README.md`
- `tools/README.md`
- `tools/abyssworker/client/README.md`
- `tools/alcatraz/README.md`
- `tools/blister/README.md`
- `tools/ghostpulse/README.md`
- `tools/guloader/README.md`
- `tools/icedid/README.md`
- `tools/ida_scripts/README.md`
- `tools/latrodectus/README.md`
- `tools/malware_research/README.md`
- `tools/shellter/README.md`
- `tools/stix-to-ecs/README.md`
- `tools/warmcookie/README.md`

### Workflows
_None found_
