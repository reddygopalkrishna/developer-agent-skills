# Hardened Deployment baseline

A complete starting point for a stateless HTTP service. Replace names, image, ports, paths and numbers; size resources from real usage. Validate with `kubectl apply --dry-run=server -f <file>` against your cluster, since field support varies by version.

## Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orders-api
  namespace: orders
  labels:
    app.kubernetes.io/name: orders-api
    app.kubernetes.io/instance: orders-api
    app.kubernetes.io/version: "1.4.2"
    app.kubernetes.io/component: api
    app.kubernetes.io/part-of: orders
    app.kubernetes.io/managed-by: kustomize
spec:
  # replicas omitted: the HPA below owns the replica count
  revisionHistoryLimit: 5
  minReadySeconds: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: orders-api
      app.kubernetes.io/instance: orders-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: orders-api
        app.kubernetes.io/instance: orders-api
        app.kubernetes.io/version: "1.4.2"
    spec:
      serviceAccountName: orders-api
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 45
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: orders-api
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: orders-api
      containers:
        - name: api
          # pin by digest (or an immutable tag); never :latest
          image: registry.example.com/orders-api@sha256:REPLACE_WITH_DIGEST
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
          envFrom:
            - configMapRef:
                name: orders-api-config
          env:
            - name: DATABASE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: orders-api-secrets
                  key: database-password
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              memory: 256Mi
              # cpu limit intentionally omitted to avoid throttling; add one if your policy requires it
          startupProbe:
            httpGet:
              path: /healthz/live
              port: http
            periodSeconds: 5
            failureThreshold: 30      # up to 150s to start
          readinessProbe:
            httpGet:
              path: /healthz/ready
              port: http
            periodSeconds: 5
            timeoutSeconds: 2
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /healthz/live    # process health only, no dependency checks
              port: http
            periodSeconds: 10
            timeoutSeconds: 2
            failureThreshold: 6
          lifecycle:
            preStop:
              exec:
                # needs a `sleep` binary in the image; see SKILL.md for alternatives
                command: ["sleep", "5"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            privileged: false
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
```

## Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: orders-api
  namespace: orders
  labels:
    app.kubernetes.io/name: orders-api
spec:
  selector:
    app.kubernetes.io/name: orders-api
    app.kubernetes.io/instance: orders-api
  ports:
    - name: http
      port: 80
      targetPort: http
```

## PodDisruptionBudget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: orders-api
  namespace: orders
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: orders-api
      app.kubernetes.io/instance: orders-api
```

## HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orders-api
  namespace: orders
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orders-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70   # percent of the CPU *request*
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
```

## ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orders-api
  namespace: orders
automountServiceAccountToken: false
```

## NetworkPolicy (default deny plus allow)

Requires a CNI plugin that enforces NetworkPolicy. Adjust the ingress source to your ingress controller's namespace and labels.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: orders
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: orders-api
  namespace: orders
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: orders-api
  policyTypes: ["Ingress", "Egress"]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - port: 8080
  egress:
    - to:   # DNS
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - port: 53
          protocol: UDP
        - port: 53
          protocol: TCP
    - to:   # database subnet; replace with your CIDR or selector
        - ipBlock:
            cidr: 10.20.0.0/16
      ports:
        - port: 5432
```

## Namespace with Pod Security Standards

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: orders
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Review notes

- If the image runs as root or writes outside `/tmp`, fix the image (see `dockerfiles`) rather than loosening `runAsNonRoot` or `readOnlyRootFilesystem`.
- If `/healthz/ready` checks dependencies, make sure it reports not-ready only for dependencies the service truly cannot work without.
- `terminationGracePeriodSeconds` (45) must exceed the preStop delay (5) plus the app's drain time.
- With `minReplicas: 3` and `maxUnavailable: 1` in the PDB, a node drain proceeds one pod at a time.
