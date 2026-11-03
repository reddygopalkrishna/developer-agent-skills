# Minimal hardened pipeline examples

Each example builds and tests a Node.js app with lint/typecheck and sharded tests in parallel, builds one artifact on the main branch, and deploys it to a protected staging environment. Adapt the commands to the project's stack.

**Before using an example:**

- Replace action and template version tags with full commit SHAs (see "Pin everything" in SKILL.md). The tags below are for readability only; resolve real SHAs, never invent them.
- Replace the placeholder deploy command and cloud settings with the project's own.
- Validate the file (`actionlint` for GitHub Actions, CI Lint for GitLab) and run it on a branch first.

## GitHub Actions

`.github/workflows/ci.yml`:

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  checks:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v7            # pin to SHA
      - uses: actions/setup-node@v7          # pin to SHA
        with:
          node-version-file: .nvmrc
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck

  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      fail-fast: false
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version-file: .nvmrc
          cache: npm
      - run: npm ci
      - run: npm test -- --shard=${{ matrix.shard }}/4

  build:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: [checks, test]
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version-file: .nvmrc
          cache: npm
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v7     # pin to SHA
        with:
          name: app-${{ github.sha }}
          path: dist/
          retention-days: 14

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 15
    environment: staging                     # protection rules and secrets live on the environment
    concurrency:
      group: deploy-staging
      cancel-in-progress: false              # never cancel a deploy midway
    permissions:
      contents: read
      id-token: write                        # OIDC token for cloud login
    steps:
      - uses: actions/checkout@v7
      - uses: actions/download-artifact@v8   # pin to SHA
        with:
          name: app-${{ github.sha }}
          path: dist/
      - uses: aws-actions/configure-aws-credentials@v6   # pin to SHA; or azure/login, google-github-actions/auth
        with:
          role-to-assume: ${{ vars.DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - run: ./scripts/deploy.sh staging dist/        # placeholder: the project's deploy command
      - run: ./scripts/smoke-test.sh "${{ vars.STAGING_URL }}"
```

Notes:

- `fail-fast: false` lets all shards finish, so one run shows every failing test.
- A production job would copy `deploy-staging` with `environment: production` (configured with required reviewers) and `needs: deploy-staging`.
- The cloud trust policy for `DEPLOY_ROLE_ARN` should accept only this repository's `staging` environment in the token's `sub` claim.
- For container images, replace the artifact steps with `docker/build-push-action`, push once tagged with `${{ github.sha }}`, and deploy by digest.

## GitLab CI

`.gitlab-ci.yml`:

```yaml
stages: [check, build, deploy]

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

default:
  image: node:22-slim
  interruptible: true
  cache:
    key:
      files: [package-lock.json]
    paths: [.npm/]
  before_script:
    - npm ci --cache .npm --prefer-offline

lint:
  stage: check
  timeout: 10m
  script:
    - npm run lint
    - npm run typecheck

test:
  stage: check
  timeout: 15m
  parallel: 4
  script:
    - npm test -- --shard=$CI_NODE_INDEX/$CI_NODE_TOTAL

build:
  stage: build
  timeout: 10m
  script:
    - npm run build
  artifacts:
    paths: [dist/]
    expire_in: 2 weeks
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

deploy_staging:
  stage: deploy
  timeout: 15m
  interruptible: false          # never cancel a deploy midway
  resource_group: staging       # one deploy at a time
  environment:
    name: staging
    url: https://staging.example.com
  id_tokens:
    CLOUD_ID_TOKEN:
      aud: https://example.com  # the audience your cloud federation config expects
  script:
    - ./scripts/deploy.sh staging dist/     # placeholder: exchange CLOUD_ID_TOKEN for cloud credentials, then deploy
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

Notes:

- The `workflow: rules` block avoids duplicate pipelines (branch and merge request) for the same push.
- `lint` and `test` share a stage, so they run in parallel.
- Mark `staging` and `production` as protected environments, and use protected variables so their secrets are only exposed to protected branches.
- Pin the `image:` by digest for reproducibility, and pin any `include:` templates to a specific ref.

## Azure Pipelines

`azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include: [main]

pr:
  branches:
    include: [main]

variables:
  npm_config_cache: $(Pipeline.Workspace)/.npm

stages:
  - stage: CI
    jobs:
      - job: checks
        timeoutInMinutes: 10
        pool:
          vmImage: ubuntu-latest
        steps:
          - task: NodeTool@0
            inputs:
              versionSpec: '22.x'
          - task: Cache@2
            inputs:
              key: 'npm | "$(Agent.OS)" | package-lock.json'
              restoreKeys: |
                npm | "$(Agent.OS)"
              path: $(npm_config_cache)
          - script: npm ci
          - script: npm run lint
          - script: npm run typecheck

      - job: test
        timeoutInMinutes: 15
        pool:
          vmImage: ubuntu-latest
        strategy:
          parallel: 4
        steps:
          - task: NodeTool@0
            inputs:
              versionSpec: '22.x'
          - task: Cache@2
            inputs:
              key: 'npm | "$(Agent.OS)" | package-lock.json'
              restoreKeys: |
                npm | "$(Agent.OS)"
              path: $(npm_config_cache)
          - script: npm ci
          - script: npm test -- --shard=$(System.JobPositionInPhase)/$(System.TotalJobsInPhase)

      - job: build
        dependsOn: [checks, test]
        condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
        timeoutInMinutes: 10
        pool:
          vmImage: ubuntu-latest
        steps:
          - task: NodeTool@0
            inputs:
              versionSpec: '22.x'
          - script: npm ci
          - script: npm run build
          - publish: dist
            artifact: app

  - stage: DeployStaging
    dependsOn: CI
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: deploy
        timeoutInMinutes: 15
        environment: staging          # approvals and checks are configured on the environment
        pool:
          vmImage: ubuntu-latest
        strategy:
          runOnce:
            deploy:
              steps:
                - download: current
                  artifact: app
                - task: AzureCLI@2
                  inputs:
                    azureSubscription: staging-federated   # service connection using workload identity federation
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      echo "Deploy $(Pipeline.Workspace)/app here with the project's deploy command"
```

Notes:

- Deployment jobs do not check out the repository by default. Add `- checkout: self` if the deploy needs scripts from the repo.
- Configure approvals, branch control and exclusive-lock checks on the `staging` and `production` environments in Azure DevOps.
- Pin template repositories (`resources: repositories:`) to a specific `ref`, and restrict which pipelines can use each service connection.
