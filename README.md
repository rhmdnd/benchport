# Benchport

This project is an attempt at parsing Center for Internet Security (CIS)
benchmarks into machine readable formats.

# Problem

There are several standard formats for security automation (XCCDF, OSCAL,
OVAL), but benchmarks are usually distributed in PDF formats. This script
attempts to convert a PDF to its text representation, parse it into individual
controls, and output those controls in a machine-format like JSON.

# Usage

You must have `pdftotext` installed, which is provided by `poppler-utils`.

```
usage: Parse information from benchmarks [-h] [-c CONTROL] benchmark

positional arguments:
  benchmark             File path to benchmark in PDF format

options:
  -h, --help            show this help message and exit
  -c CONTROL, --control CONTROL
                        Control ID to parse and print to stdout in YAML (e.g, 1.1.2).
```

Output an entire benchmark:

```
$ python bp.py CIS_RedHat_OpenShift_Container_Platform_v4_Benchmark_v1.1.0.pdf
```

Parse a specific control from the benchmark:
```
$ python bp.py CIS_RedHat_OpenShift_Container_Platform_v4_Benchmark_v1.1.0.pdf -c 1.2.1
{"section": "1.2.1", "title": "Ensure that anonymous requests are authorized (Manual)", "description": "When anonymous requests to the API server are allowed, they must be authorized.", "rationale": "When enabled, requests that are not rejected by other configured authentication methods are treated as anonymous requests. These requests are then served by the API server. You should rely on authentication to authorize anonymous requests. If you are using RBAC authorization, it is generally considered reasonable to allow anonymous access to the API Server for health checks and discovery purposes, and hence this recommendation is not scored. However, you should consider whether anonymous discovery is an acceptable risk for your purposes.", "impact": null, "profile_applicability": "Level 1"}
```

Use `jq` to filter results:

```
$ python bp.py CIS_RedHat_OpenShift_Container_Platform_v4_Benchmark_v1.1.0.pdf -c 1.2.1 | jq .description
"When anonymous requests to the API server are allowed, they must be authorized."
```

Search for specific controls using `jq`:

```
$ python bp.py ../benchmarks/CIS_RedHat_OpenShift_Container_Platform_v4_Benchmark_v1.1.0.pdf | jq '.[] | select(.section=="5.1.1")'
{
  "section": "5.1.1",
  "title": "role is only used where required (Manual)",
  "description": "The RBAC role cluster-admin provides wide-ranging powers over the environment and should be used only where and when needed.",
  "rationale": "Kubernetes provides a set of default roles where RBAC is used. Some of these roles such as cluster-admin provide wide-ranging privileges which should only be applied where absolutely necessary. Roles such as cluster-admin allow super-user access to perform any action on any resource. When used in a ClusterRoleBinding, it gives full control over every resource in the cluster and in all namespaces. When used in a RoleBinding, it gives full control over every resource in the rolebinding's namespace, including the namespace itself.",
  "impact": "Care should be taken before removing any clusterrolebindings from the environment to ensure they were not required for operation of the cluster. Specifically, modifications should not be made to clusterrolebindings with the system: prefix as they are required for the operation of system components.",
  "profile_applicability": "Level 1"
}
```

# Unit Testing

You can test benchport locally using unit tests, but you must supply the
benchmark in PDF format and the assertions to match the benchmark against as a
YAML file.

The following is an example YAML assertion file:

```yaml
1.1.2:
  section: "1.1.2"
  title: >-
    Ensure that the API server pod specification file ownership is set to
    root:root (Manual)
  profile_applicability: "Level 1"
  description: >-
    Ensure that the API server pod specification file ownership is set to
    root:root.
  rationale: >-
    The API server pod specification file controls various parameters that set
    the behavior of the API server. You should set its file ownership to
    maintain the integrity of the file. The file should be owned by root:root.
  impact: null
  audit: |-
    OpenShift 4 deploys two API servers: the OpenShift API server and the Kube API server.
    The OpenShift API server is managed as a deployment. The pod specification yaml for
    openshift-apiserver is stored in etcd.
    The Kube API Server is managed as a static pod. The pod specification file for the kubeapiserver is created on the control plane nodes at /etc/kubernetes/manifests/kubeapiserver-pod.yaml. The kube-apiserver is mounted via hostpath to the kube-apiserver
    pods via /etc/kubernetes/static-pod-resources/kube-apiserver-pod.yaml with ownership
    root:root.
    To verify pod specification file ownership for the kube-apiserver, run the following
    command.
    #echo “check kube-apiserver pod specification file ownership”
    for i in $( oc get pods -n openshift-kube-apiserver -l app=openshift-kubeapiserver -o name )
    do
    oc exec -n openshift-kube-apiserver $i -- \
    stat -c %U:%G /etc/kubernetes/static-pod-resources/kube-apiserver-pod.yaml
    done

    Verify that the ownership is set to root:root.
  remediation: >-
    No remediation required; file permissions are managed by the operator.
  default: >-
    By default, in OpenShift 4, the kube-apiserver-pod.yaml file ownership is
    set to root:root.
  references: |-
    1. https://docs.openshift.com/container-platform/4.3/architecture/controlplane.html#defining-masters_control-plane
    2. https://docs.openshift.com/container-platform/4.5/operators/operatorreference.html#kube-apiserver-operator_red-hat-operators
    3. https://docs.openshift.com/container-platform/4.5/operators/operatorreference.html#openshift-apiserver-operator_red-hat-operators
    4. https://kubernetes.io/docs/reference/command-line-tools-reference/kubeapiserver/
```

You can pass in the required benchmark and assertions using environment variables:

```
$ CONTROL_PDF=CIS_RedHat_OpenShift_Contianer_Platform_v4_Benchmark_v1.1.0.pdf ASSERTION_FILE=data.yaml python -m unittest bp/tests/test_bp.py
```

Note, official CIS benchmarks are not maintained in this repository and must be
downloaded from [CIS](https://www.cisecurity.org/) directly.

# Limitations

The following is a list of acknowledged gaps in the current design:

- HTML formatting in the PDF is not preserved
- Parsing currently assumes a required property order (e.g., Description must
  come before Rationale)
- The `Control` object isn't available via a package, this may change in the
  future
