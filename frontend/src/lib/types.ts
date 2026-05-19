// Mirror of backend/app/models.py. Keep these in sync: the backend
// returns these shapes verbatim with camelCase aliases.

export type ProviderType =
  | 'custom' | 'openai' | 'anthropic' | 'huggingface' | 'cohere'
  | 'azure_openai' | 'bedrock' | 'vertex';
export type Environment = 'dev' | 'stage' | 'prod';
export type InferenceFramework =
  | 'vllm' | 'tgi' | 'triton' | 'llama_cpp' | 'ollama' | 'custom';
export type EndpointType = 'publicAPI' | 'internalAPI';
export type Protocol = 'http' | 'https' | 'grpc';
export type AuthType = 'none' | 'api_key' | 'bearer' | 'mtls' | 'oauth2';
export type Operation =
  | 'chatCompletion' | 'completion' | 'embeddings' | 'rerank' | 'image' | 'audio';

export type EntityType =
  | 'model' | 'deployment' | 'endpoint' | 'ragPipeline'
  | 'vectorIndex' | 'tool' | 'agent' | 'safetyPolicy';

export interface Architecture {
  numLayers?: number;
  hiddenSize?: number;
  numHeads?: number;
  vocabSize?: number;
  maxContext?: number;
  quantization?: string;
}
export interface TrainingLineage {
  baseModel?: string;
  fineTuningType?: string;
  createdAt?: string;
  tags: string[];
}
export interface Resources {
  numReplicas: number;
  gpusPerReplica: number;
  gpuType?: string;
  totalVRAM?: number;
}
export interface DeploymentConfig {
  maxBatchSize?: number;
  maxTokens?: number;
  temperatureMin?: number;
  temperatureMax?: number;
  extra: Record<string, unknown>;
}
export interface RetrievalConfig {
  k: number;
  filters: Record<string, unknown>;
  rerankers: string[];
}
export interface SafetyFilter {
  name: string;
  description?: string;
  pattern?: string;
}

export interface Model {
  id: string;
  name: string;
  version?: string;
  providerType: ProviderType;
  architecture: Architecture;
  training: TrainingLineage;
}
export interface Deployment {
  id: string;
  modelId: string;
  environment: Environment;
  region?: string;
  inferenceFramework: InferenceFramework;
  resources: Resources;
  configuration: DeploymentConfig;
}
export interface Endpoint {
  id: string;
  deploymentId: string;
  type: EndpointType;
  protocol: Protocol;
  url: string;
  authType: AuthType;
  supportedOperations: Operation[];
  healthPath: string;
}
export interface VectorIndex {
  id: string;
  name: string;
  dbType: string;
  collectionName: string;
  embeddingDim: number;
  numDocuments?: number;
  avgDocLength?: number;
}
export interface RagPipeline {
  id: string;
  name: string;
  embeddingModelId: string;
  vectorIndexId: string;
  distanceMetric: string;
  retrieval: RetrievalConfig;
}
export interface Tool {
  id: string;
  name: string;
  description?: string;
  inputSchema: Record<string, unknown>;
  outputSchema: Record<string, unknown>;
  backingService?: string;
}
export interface SafetyPolicy {
  id: string;
  name: string;
  prePromptFilters: SafetyFilter[];
  postResponseFilters: SafetyFilter[];
  safetyModelId?: string;
}
export interface Agent {
  id: string;
  name: string;
  role?: string;
  primaryModelId: string;
  toolsUsed: string[];
  ragPipelinesUsed: string[];
  safetyPolicyId?: string;
}

export interface MetricsSnapshot {
  entityType: EntityType;
  entityId: string;
  latencyP50: number;
  latencyP95: number;
  tokensPerSecond?: number;
  errorRate: number;
  gpuUtilization?: number;
  timeRange: '1h' | '24h';
  sampledAt: string;
}

export interface Graph {
  models: Model[];
  deployments: Deployment[];
  endpoints: Endpoint[];
  ragPipelines: RagPipeline[];
  vectorIndexes: VectorIndex[];
  tools: Tool[];
  agents: Agent[];
  safetyPolicies: SafetyPolicy[];
}

export type AnyEntity =
  | (Model & { _type: 'model' })
  | (Deployment & { _type: 'deployment' })
  | (Endpoint & { _type: 'endpoint' })
  | (RagPipeline & { _type: 'ragPipeline' })
  | (VectorIndex & { _type: 'vectorIndex' })
  | (Tool & { _type: 'tool' })
  | (Agent & { _type: 'agent' })
  | (SafetyPolicy & { _type: 'safetyPolicy' });
