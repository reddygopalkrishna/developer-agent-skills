# Plan review checklist

Use this for Terraform/OpenTofu plans, Bicep/ARM what-if, Pulumi previews and CDK/CloudFormation diffs. Read the whole output; the dangerous line is often in the middle.

## 0. Is this the right target?

- [ ] Correct cloud account / subscription / project (check the provider config and credentials in use).
- [ ] Correct workspace, stack or environment directory.
- [ ] Correct region.
- [ ] Plan was made from the commit you intend to deploy, with current state (no stale saved plan).

## 1. Read the summary line

Terraform/OpenTofu ends with `Plan: X to add, Y to change, Z to destroy.`

- [ ] Do the counts match what the change should do? A one-line tag change should not show resources to destroy.
- [ ] If Z is greater than 0, list every destroyed resource by address before continuing.

## 2. Find destructive actions

Search the plan text for these markers:

| Marker | Meaning |
| --- | --- |
| `will be destroyed` / `-` | Resource deleted |
| `must be replaced` / `-/+` | Deleted then recreated (default order) |
| `+/-` | Created then deleted (`create_before_destroy`) |
| `# forces replacement` | The attribute that triggered replacement |
| `(known after apply)` on IDs, names or IPs | Value will change; dependents may break |
| What-if `Delete` | Resource removed (Complete mode or explicit) |
| Pulumi `replace`, `delete` | Same meaning |
| CloudFormation `Replacement: True` | Same meaning |

For each one ask:

- [ ] Does this resource hold data (database, disk, bucket, file share, queue, key vault/KMS key, DNS zone, log store)? If yes, replacement may mean **data loss**. Stop and confirm a backup or a non-replacing alternative.
- [ ] Does anything depend on its identity (IP address, hostname, ARN/resource ID, certificate, connection string)? Replacement may break clients.
- [ ] Is downtime acceptable while it is recreated?
- [ ] Is the replacement caused by a rename or move? Use a `moved` block / alias instead.
- [ ] Is it caused by a provider upgrade changing defaults? Pin the attribute explicitly.

## 3. Review in-place changes

- [ ] Security groups, firewall rules, NSGs: is anything opened to `0.0.0.0/0` or `::/0` that wasn't before?
- [ ] IAM / RBAC: new permissions, wildcards (`*` actions or resources), new trust relationships, roles assigned at broad scopes?
- [ ] Encryption, public access, TLS settings: anything turned off or downgraded?
- [ ] Network: routes, peering, private endpoints, DNS records changed?
- [ ] Scaling and sizing: instance types, node counts, SKUs, storage size (cost and capacity impact)?
- [ ] Deletion protection, backups, retention, versioning: anything reduced?
- [ ] Changes you did not make (drift or another person's unmerged work)? Find out why before applying.

## 4. Unexpected noise

- [ ] Perpetual diffs (the same change shows on every plan): usually ordering, defaults or computed values. Fix in code (explicit values, `ignore_changes` only with a comment explaining why).
- [ ] Changes to many resources from one variable: confirm that was intended.

## 5. Cost and limits

- [ ] New expensive resources (large instances, managed databases, NAT gateways, load balancers, GPUs) called out. Run a cost diff if the repo uses one.
- [ ] Quota or limit risk (IP ranges, vCPU quotas, resource count limits).

## 6. Summary to the user

Write it before asking to apply:

```text
Target: <account/subscription>, <environment>, <region>
Plan: 3 to add, 1 to change, 1 to destroy
Destroy / replace:
  - module.db.azurerm_postgresql_flexible_server.main (REPLACE: forces replacement on `zone`)
    -> holds production data; replacement would delete it. Recommend: revert zone change.
Security-relevant changes:
  - aws_security_group.web: ingress 443 from 0.0.0.0/0 (new)
Expected downtime: none / <describe>
Cost impact: <estimate or "not measured">
Apply command (after your OK): terraform apply tfplan
```

Do not apply until the user explicitly confirms after reading this summary.

## Tool-specific commands

| Tool | Save / show plan | Apply reviewed plan |
| --- | --- | --- |
| Terraform / OpenTofu | `terraform plan -out=tfplan`; `terraform show tfplan`; `terraform show -json tfplan` | `terraform apply tfplan` |
| Bicep / ARM | `az deployment group what-if --resource-group <rg> --template-file main.bicep --parameters <file>` | `az deployment group create ...` (or `--confirm-with-what-if`) |
| Pulumi | `pulumi preview --diff` | `pulumi up` (review the preview it shows; avoid `--yes` without confirmation) |
| CDK | `cdk diff` | `cdk deploy` |
| CloudFormation | Create a change set and describe it | Execute the change set |

Check each tool's `--help` for flags in the installed version.
