"""Nuclide Atlas — canonical LLM-stack schema.

These Pydantic v2 models are the single source of truth for the inspector's
graph. The frontend mirrors them as TypeScript interfaces in
`frontend/src/lib/types.ts`. Add a field here, mirror it there.

Relations between entities are expressed as string ID references
(`*Id` / `*Ids` fields), never as nested objects. This keeps the graph
trivially traversable on both ends — the frontend's agent-path-highlight
feature relies on it.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        use_enum_values=True,
    )


class ProviderType(str, Enum):
    custom = "custom"
    openai = "openai"
    anthropic = "anthropic"
    huggingface = "huggingface"
    cohere = "cohere"
    azure_openai = "azure_openai"
    bedrock = "bedrock"
    vertex = "vertex"


class Environment(str, Enum):
    dev = "dev"
    stage = "stage"
    prod = "prod"


class InferenceFramework(str, Enum):
    vllm = "vllm"
    tgi = "tgi"
    triton = "triton"
    llama_cpp = "llama_cpp"
    ollama = "ollama"
    custom = "custom"


class EndpointType(str, Enum):
    public_api = "publicAPI"
    internal_api = "internalAPI"


class Protocol(str, Enum):
    http = "http"
    https = "https"
    grpc = "grpc"


class AuthType(str, Enum):
    none = "none"
    api_key = "api_key"
    bearer = "bearer"
    mtls = "mtls"
    oauth2 = "oauth2"


class Operation(str, Enum):
    chat_completion = "chatCompletion"
    completion = "completion"
    embeddings = "embeddings"
    rerank = "rerank"
    image = "image"
    audio = "audio"


class EntityType(str, Enum):
    model = "model"
    deployment = "deployment"
    endpoint = "endpoint"
    rag_pipeline = "ragPipeline"
    vector_index = "vectorIndex"
    tool = "tool"
    agent = "agent"
    safety_policy = "safetyPolicy"


# ── leaves ──────────────────────────────────────────────────────────────

class Architecture(_Base):
    """Model architecture metadata. Fields are optional because we won't
    always know them — a closed OpenAI model exposes none of this."""
    num_layers: int | None = Field(default=None, alias="numLayers")
    hidden_size: int | None = Field(default=None, alias="hiddenSize")
    num_heads: int | None = Field(default=None, alias="numHeads")
    vocab_size: int | None = Field(default=None, alias="vocabSize")
    max_context: int | None = Field(default=None, alias="maxContext")
    quantization: str | None = None


class TrainingLineage(_Base):
    base_model: str | None = Field(default=None, alias="baseModel")
    fine_tuning_type: str | None = Field(default=None, alias="fineTuningType")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    tags: list[str] = Field(default_factory=list)


class Resources(_Base):
    num_replicas: int = Field(default=1, alias="numReplicas")
    gpus_per_replica: int = Field(default=0, alias="gpusPerReplica")
    gpu_type: str | None = Field(default=None, alias="gpuType")
    total_vram_gb: float | None = Field(default=None, alias="totalVRAM")


class DeploymentConfig(_Base):
    max_batch_size: int | None = Field(default=None, alias="maxBatchSize")
    max_tokens: int | None = Field(default=None, alias="maxTokens")
    temperature_min: float | None = Field(default=None, alias="temperatureMin")
    temperature_max: float | None = Field(default=None, alias="temperatureMax")
    extra: dict[str, Any] = Field(default_factory=dict)


class RetrievalConfig(_Base):
    k: int = 5
    filters: dict[str, Any] = Field(default_factory=dict)
    rerankers: list[str] = Field(default_factory=list)


class SafetyFilter(_Base):
    name: str
    description: str | None = None
    pattern: str | None = None  # regex or rule reference


# ── nodes ───────────────────────────────────────────────────────────────

class Model(_Base):
    id: str
    name: str
    version: str | None = None
    provider_type: ProviderType = Field(alias="providerType")
    architecture: Architecture = Field(default_factory=Architecture)
    training: TrainingLineage = Field(default_factory=TrainingLineage)


class Deployment(_Base):
    id: str
    model_id: str = Field(alias="modelId")
    environment: Environment
    region: str | None = None
    inference_framework: InferenceFramework = Field(alias="inferenceFramework")
    resources: Resources = Field(default_factory=Resources)
    configuration: DeploymentConfig = Field(default_factory=DeploymentConfig)


class Endpoint(_Base):
    id: str
    deployment_id: str = Field(alias="deploymentId")
    type: EndpointType
    protocol: Protocol
    url: str
    auth_type: AuthType = Field(alias="authType")
    supported_operations: list[Operation] = Field(
        default_factory=list, alias="supportedOperations"
    )
    # path templates the prober will try; defaults to OpenAI-compatible
    health_path: str = Field(default="/v1/models", alias="healthPath")


class VectorIndex(_Base):
    id: str
    name: str
    db_type: str = Field(alias="dbType")  # qdrant, pinecone, weaviate, milvus, ...
    collection_name: str = Field(alias="collectionName")
    embedding_dim: int = Field(alias="embeddingDim")
    num_documents: int | None = Field(default=None, alias="numDocuments")
    avg_doc_length: float | None = Field(default=None, alias="avgDocLength")


class RagPipeline(_Base):
    id: str
    name: str
    embedding_model_id: str = Field(alias="embeddingModelId")
    vector_index_id: str = Field(alias="vectorIndexId")
    distance_metric: str = Field(default="cosine", alias="distanceMetric")
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)


class Tool(_Base):
    id: str
    name: str
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema")
    output_schema: dict[str, Any] = Field(default_factory=dict, alias="outputSchema")
    backing_service: str | None = Field(
        default=None, alias="backingService"
    )  # sqlDb | restApi | knowledgeGraph | ...


class SafetyPolicy(_Base):
    id: str
    name: str
    pre_prompt_filters: list[SafetyFilter] = Field(
        default_factory=list, alias="prePromptFilters"
    )
    post_response_filters: list[SafetyFilter] = Field(
        default_factory=list, alias="postResponseFilters"
    )
    safety_model_id: str | None = Field(default=None, alias="safetyModelId")


class Agent(_Base):
    id: str
    name: str
    role: str | None = None
    primary_model_id: str = Field(alias="primaryModelId")
    tools_used: list[str] = Field(default_factory=list, alias="toolsUsed")
    rag_pipelines_used: list[str] = Field(
        default_factory=list, alias="ragPipelinesUsed"
    )
    safety_policy_id: str | None = Field(default=None, alias="safetyPolicyId")


# ── metrics ─────────────────────────────────────────────────────────────

class TimeRange(str, Enum):
    last_1h = "1h"
    last_24h = "24h"


class MetricsSnapshot(_Base):
    entity_type: EntityType = Field(alias="entityType")
    entity_id: str = Field(alias="entityId")
    latency_p50_ms: float = Field(alias="latencyP50")
    latency_p95_ms: float = Field(alias="latencyP95")
    tokens_per_second: float | None = Field(default=None, alias="tokensPerSecond")
    error_rate: float = Field(alias="errorRate")
    gpu_utilization: float | None = Field(default=None, alias="gpuUtilization")
    time_range: TimeRange = Field(default=TimeRange.last_1h, alias="timeRange")
    sampled_at: datetime = Field(default_factory=datetime.utcnow, alias="sampledAt")


# ── envelope ────────────────────────────────────────────────────────────

class Graph(_Base):
    """Top-level inventory. /api/graph returns this serialized as JSON
    with `by_alias=True` so the frontend gets camelCase keys."""
    models: list[Model] = Field(default_factory=list)
    deployments: list[Deployment] = Field(default_factory=list)
    endpoints: list[Endpoint] = Field(default_factory=list)
    rag_pipelines: list[RagPipeline] = Field(
        default_factory=list, alias="ragPipelines"
    )
    vector_indexes: list[VectorIndex] = Field(
        default_factory=list, alias="vectorIndexes"
    )
    tools: list[Tool] = Field(default_factory=list)
    agents: list[Agent] = Field(default_factory=list)
    safety_policies: list[SafetyPolicy] = Field(
        default_factory=list, alias="safetyPolicies"
    )
