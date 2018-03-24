import os
import base64

from kubernetes import config as kube_config
from kubernetes import client as kube_client
from kubernetes.client import V1ObjectFieldSelector
from kubernetes.client.models.v1_delete_options import V1DeleteOptions
from kubernetes.client.models.v1_job import V1Job
from kubernetes.client.models.v1_job_spec import V1JobSpec
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_container import V1Container
from kubernetes.client.models.v1_pod_spec import V1PodSpec
from kubernetes.client.models.v1_pod_template_spec import V1PodTemplateSpec
from kubernetes.client.models.v1_local_object_reference import V1LocalObjectReference
from kubernetes.client.models.v1_env_var import V1EnvVar
from kubernetes.client.models.v1_env_var_source import V1EnvVarSource
from kubernetes.client.models.v1_secret_key_selector import V1SecretKeySelector
from kubernetes.client.models.v1_volume_mount import V1VolumeMount
from kubernetes.client.models.v1_volume import V1Volume
from kubernetes.client.models.v1_azure_file_volume_source import V1AzureFileVolumeSource


def get_current_namespace() -> str:
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", mode='r') as handler:
        return handler.readline()


def clean_up_jobs(run_id: str, job_name: str) -> None:
    kube_config.load_incluster_config()
    ns = get_current_namespace()  # pylint: disable=invalid-name

    controller_jobs = kube_client.BatchV1Api().list_namespaced_job(namespace=ns, label_selector=f"run_id={run_id}")

    for job in controller_jobs.items:
        kube_client.BatchV1Api().delete_namespaced_job(name=job.metadata.name,
                                                       namespace=ns,
                                                       body=V1DeleteOptions(propagation_policy='Background'))

    if not job_name:
        return

    test_jobs = kube_client.BatchV1Api().list_namespaced_job(namespace=ns, label_selector=f"job-name={job_name}")
    for job in test_jobs.items:
        kube_client.BatchV1Api().delete_namespaced_job(name=job.metadata.name,
                                                       namespace=ns,
                                                       body=V1DeleteOptions(propagation_policy='Background'))


def create_controller_job(run_id: str, live: bool, image: str, agentver: str) -> V1Job:
    print(f'Create new controller job for run {run_id} ...')

    random_tag = base64.b32encode(os.urandom(4)).decode("utf-8").lower().rstrip('=')
    ctrl_job_name = f'ctrl-{run_id}-{random_tag}'
    labels = {'run_id': str(run_id), 'run_live': str(live)}

    kube_config.load_incluster_config()
    api = kube_client.BatchV1Api()

    return api.create_namespaced_job(
        namespace=get_current_namespace(),
        body=V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=V1ObjectMeta(name=ctrl_job_name, labels=labels),
            spec=V1JobSpec(
                backoff_limit=3,
                template=V1PodTemplateSpec(
                    metadata=V1ObjectMeta(name=ctrl_job_name, labels=labels),
                    spec=V1PodSpec(
                        containers=[V1Container(
                            name='main',
                            image=image,
                            command=['/mnt/agents/a01dispatcher', '-run', str(run_id)],
                            env=[
                                V1EnvVar(name='A01_INTERNAL_COMKEY', value_from=V1EnvVarSource(
                                    secret_key_ref=V1SecretKeySelector(name='store-secrets', key='comkey'))),
                                V1EnvVar(name='ENV_POD_NAME', value_from=V1EnvVarSource(
                                    field_ref=V1ObjectFieldSelector(field_path='metadata.name')))
                            ],
                            volume_mounts=[
                                V1VolumeMount(mount_path='/mnt/agents', name='agents-storage', read_only=True)
                            ]
                        )],
                        image_pull_secrets=[V1LocalObjectReference(name='azureclidev-registry')],
                        volumes=[V1Volume(name='agents-storage',
                                          azure_file=V1AzureFileVolumeSource(read_only=True,
                                                                             secret_name='agent-secrets',
                                                                             share_name=f'linux-{agentver}'))],
                        restart_policy='Never')
                )
            )))
