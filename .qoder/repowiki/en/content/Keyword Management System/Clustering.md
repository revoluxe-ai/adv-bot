# Clustering

<cite>
**Referenced Files in This Document**   
- [word_to_vec_object.py](file://app/modules/wb_adv_updater/word_to_vec_object.py)
- [faiss_index_manager.py](file://app/utils/faiss_manager/faiss_index_manager.py)
- [faiss_index.py](file://app/utils/faiss_manager/faiss_index.py)
- [Transformers.py](file://app/utils/text_master/Transformers.py)
- [driver.py](file://app/utils/NeoDataScience/driver.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [clusters.py](file://app/client_bot/user_interface/handlers/clusters.py)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Core Components](#core-components)
3. [Architecture Overview](#architecture-overview)
4. [Keyword Clustering Workflow](#keyword-clustering-workflow)
5. [Vectorization and Semantic Representation](#vectorization-and-semantic-representation)
6. [FAISS-Based Similarity Search](#faiss-based-similarity-search)
7. [Clustering Process Implementation](#clustering-process-implementation)
8. [Integration with ML Pipeline](#integration-with-ml-pipeline)
9. [Use Cases: Bid Group Optimization and Campaign Structuring](#use-cases-bid-group-optimization-and-campaign-structuring)
10. [Common Issues and Tuning Recommendations](#common-issues-and-tuning-recommendations)
11. [Performance Considerations](#performance-considerations)
12. [Conclusion](#conclusion)

## Introduction
The Keyword Clustering sub-feature enables semantic grouping of advertising keywords using vector embeddings and similarity search. This system leverages word2vec technology for semantic representation and FAISS (Facebook AI Similarity Search) for efficient nearest-neighbor lookups. The clustering process supports bid group optimization and campaign structuring by identifying semantically related keywords. This document details the implementation workflow, integration points, performance characteristics, and tuning strategies for large-scale keyword clustering operations.

## Core Components
The keyword clustering system consists of several interconnected components responsible for vectorization, indexing, similarity search, and cluster formation. Key modules include the word2vec model for semantic embedding, FAISS-based index management for fast similarity search, Neo4j graph database integration for relationship storage, and clustering logic for group formation.

**Section sources**
- [word_to_vec_object.py](file://app/modules/wb_adv_updater/word_to_vec_object.py#L1-L3)
- [faiss_index_manager.py](file://app/utils/faiss_manager/faiss_index_manager.py#L1-L187)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py#L1-L50)

## Architecture Overview
The keyword clustering architecture follows a pipeline pattern where keywords are first vectorized using word2vec embeddings, then indexed using FAISS for efficient similarity search, and finally grouped into clusters based on semantic proximity. The system integrates with Neo4j to store keyword relationships and with the ML pipeline for continuous model updates.

```mermaid
graph TB
subgraph "Input"
Keywords["Raw Keywords"]
end
subgraph "Processing"
Vectorizer["Word2Vec Vectorization"]
DimensionalityReduction["Optional Dimensionality Reduction"]
FAISSIndex["FAISS Index Storage"]
ClusteringEngine["Clustering Algorithm"]
end
subgraph "Storage"
Neo4j[(Neo4j Graph Database)]
Redis[(Redis Cache)]
end
subgraph "Output"
Clusters["Keyword Clusters"]
BidGroups["Bid Groups"]
Campaigns["Campaign Structures"]
end
Keywords --> Vectorizer
Vectorizer --> DimensionalityReduction
DimensionalityReduction --> FAISSIndex
FAISSIndex --> ClusteringEngine
ClusteringEngine --> Clusters
Clusters --> BidGroups
Clusters --> Campaigns
ClusteringEngine --> Neo4j
ClusteringEngine --> Redis
```

**Diagram sources**
- [word_to_vec_object.py](file://app/modules/wb_adv_updater/word_to_vec_object.py#L1-L3)
- [faiss_index_manager.py](file://app/utils/faiss_manager/faiss_index_manager.py#L1-L187)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L842-L880)

## Keyword Clustering Workflow
The clustering workflow begins with keyword ingestion and proceeds through vectorization, indexing, similarity search, and cluster formation. The process is initiated through the clusters.py handler and coordinates between multiple components to produce semantically meaningful keyword groups.

```mermaid
sequenceDiagram
participant Handler as "clusters.py"
participant Vectorizer as "Word2Vec Object"
participant FAISS as "FaissManager"
participant Neo4j as "Neo4j Driver"
participant ML as "ML DataManager"
Handler->>Vectorizer : Request keyword vectors
Vectorizer->>Vectorizer : Generate word2vec embeddings
Vectorizer-->>Handler : Return vectors
Handler->>FAISS : Store in FAISS index
FAISS->>FAISS : Build IndexFlatIP structure
FAISS-->>Handler : Index ready
Handler->>FAISS : Search similar keywords
FAISS->>FAISS : Perform similarity search
FAISS-->>Handler : Return nearest neighbors
Handler->>Neo4j : Store LIKE relationships
Neo4j-->>Handler : Confirmation
Handler->>ML : Trigger model update
ML-->>Handler : Update status
```

**Diagram sources**
- [clusters.py](file://app/client_bot/user_interface/handlers/clusters.py#L1-L20)
- [word_to_vec_object.py](file://app/modules/wb_adv_updater/word_to_vec_object.py#L1-L3)
- [faiss_index_manager.py](file://app/utils/faiss_manager/faiss_index_manager.py#L1-L187)

**Section sources**
- [clusters.py](file://app/client_bot/user_interface/handlers/clusters.py#L1-L50)
- [faiss_index_manager.py](file://app/utils/faiss_manager/faiss_index_manager.py#L1-L187)

## Vectorization and Semantic Representation
Keywords are converted into dense vector representations using the Word2Vec model loaded from the Wikipedia2Vec Russian corpus. The vectorization process computes average vectors from individual word embeddings, enabling semantic representation of multi-word phrases.

```mermaid
classDiagram
class Word2Vec {
+_model : KeyedVectors
+model_path : str
+_load_model_lock : Lock
+_load_model() : Coroutine
+average_vector_from_sentence(phrase : str) : ndarray | None
+get_norm_distance(value : float) : float
}
class Word2VecObject {
+word2vec : Word2Vec
}
Word2VecObject --> Word2Vec : "contains"
```

**Diagram sources**
- [Transformers.py](file://app/utils/text_master/Transformers.py#L1-L88)
- [word_to_vec_object.py](file://app/modules/wb_adv_updater/word_to_vec_object.py#L1-L3)

**Section sources**
- [Transformers.py](file://app/utils/text_master/Transformers.py#L1-L88)
- [word_to_vec_object.py](file://app/modules/wb_adv_updater/word_to_vec_object.py#L1-L3)

## FAISS-Based Similarity Search
The system uses FAISS with IndexFlatIP (Inner Product) for efficient similarity search between keyword vectors. The FaissManager class handles index creation, loading, and querying, supporting both keyword and keyword phrase indexing with cosine similarity metrics.

```mermaid
classDiagram
class FaissManager {
+__init__(batch_size : int, load_keywords : bool, load_images : bool, load_keyword_phrase : bool)
+keywords : Index
+keyword_phrases : Index
+_get_keywords_index(vector_property : str) : Index
+get_keyword_phrases_index() : Index
+__get_file_path(file_name : str) : str
}
class Index {
+__init__(objects : Union[Query, List], vector_property_name : str, file_path : str, index_type : str, batch_size : int)
+index : faiss.IndexIDMap
+_file_path : str
+__create_new_index() : faiss.IndexIDMap
+get_near_object_id(vector : list[float]) : int
+save_index() : void
}
FaissManager --> Index : "creates"
```

**Diagram sources**
- [faiss_index_manager.py](file://app/utils/faiss_manager/faiss_index_manager.py#L1-L187)
- [faiss_index.py](file://app/utils/faiss_manager/faiss_index.py#L1-L105)

**Section sources**
- [faiss_index_manager.py](file://app/utils/faiss_manager/faiss_index_manager.py#L1-L187)
- [faiss_index.py](file://app/utils/faiss_manager/faiss_index.py#L1-L105)

## Clustering Process Implementation
The clustering process involves creating a graph projection in Neo4j using keyword vectors, executing KNN (k-nearest neighbors) algorithms to identify semantic relationships, and storing LIKE relationships with similarity scores. This enables formation of clusters based on semantic proximity rather than exact keyword matching.

```mermaid
flowchart TD
Start([Start Clustering]) --> LoadVectors["Load keyword vectors from Neo4j"]
LoadVectors --> CreateGraph["Create GDS graph projection with word2vec properties"]
CreateGraph --> ExecuteKNN["Execute KNN algorithm with cosine similarity"]
ExecuteKNN --> StoreRelationships["Store LIKE relationships with similarity scores"]
StoreRelationships --> FormClusters["Form clusters from connected components"]
FormClusters --> OptimizeBids["Optimize bid groups based on clusters"]
OptimizeBids --> StructureCampaigns["Structure campaigns using semantic groups"]
StructureCampaigns --> End([End Clustering])
```

**Diagram sources**
- [driver.py](file://app/utils/NeoDataScience/driver.py#L461-L499)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py#L36-L52)

**Section sources**
- [driver.py](file://app/utils/NeoDataScience/driver.py#L461-L499)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py#L36-L52)

## Integration with ML Pipeline
The clustering system integrates with the ML pipeline through the ml_data_manager.py module, enabling continuous model updates based on new keyword data and clustering results. This ensures the word2vec model and clustering patterns evolve with changing market language and user behavior.

```mermaid
sequenceDiagram
participant Clustering as "Clustering System"
participant MLManager as "ML DataManager"
participant ModelStorage as "Model Storage"
participant FeedbackLoop as "Performance Feedback"
Clustering->>MLManager : Send new keyword vectors
MLManager->>ModelStorage : Update word2vec model
ModelStorage-->>MLManager : Confirmation
MLManager->>MLManager : Retrain clustering model
MLManager->>FeedbackLoop : Collect campaign performance data
FeedbackLoop-->>MLManager : Return performance metrics
MLManager->>Clustering : Send updated model parameters
```

**Diagram sources**
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py#L1-L50)
- [word_to_vec_object.py](file://app/modules/wb_adv_updater/word_to_vec_object.py#L1-L3)

**Section sources**
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py#L1-L50)

## Use Cases: Bid Group Optimization and Campaign Structuring
Clustered keywords enable strategic bid group optimization and campaign structuring by grouping semantically related terms. This allows for more efficient budget allocation, improved ad relevance, and better performance tracking at the cluster level rather than individual keyword level.

```mermaid
erDiagram
KEYWORD_CLUSTER {
uuid cluster_id PK
string cluster_name
timestamp created_at
timestamp updated_at
float average_cpc
int keyword_count
enum status
}
KEYWORD {
uuid keyword_id PK
string text UK
float vector[100]
timestamp created_at
timestamp updated_at
}
BID_GROUP {
uuid bid_group_id PK
string name
float default_bid
float max_bid
float min_bid
enum strategy
}
CAMPAIGN {
uuid campaign_id PK
string name
float budget
timestamp start_date
timestamp end_date
enum status
}
KEYWORD_CLUSTER ||--o{ KEYWORD : "contains"
KEYWORD_CLUSTER ||--|| BID_GROUP : "maps_to"
BID_GROUP ||--o{ CAMPAIGN : "belongs_to"
```

**Diagram sources**
- [clusters.py](file://app/client_bot/user_interface/handlers/clusters.py#L1-L20)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py#L1-L50)

**Section sources**
- [clusters.py](file://app/client_bot/user_interface/handlers/clusters.py#L1-L50)

## Common Issues and Tuning Recommendations
The system may encounter issues such as over-clustering (too many small clusters) or semantic drift (clusters losing coherence over time). These can be addressed through parameter tuning, model refresh rates, and similarity threshold adjustments.

### Common Issues:
- **Over-clustering**: Caused by overly sensitive similarity thresholds
- **Semantic drift**: Occurs when model isn't updated frequently enough
- **Cold start problem**: New keywords without vector representations
- **Memory pressure**: Large index loading times and memory usage

### Tuning Recommendations:
- Adjust KNN parameters (k-value, similarity threshold)
- Implement periodic model retraining schedules
- Use dimensionality reduction for high-dimensional vectors
- Implement caching strategies for frequently accessed clusters
- Monitor cluster quality metrics and adjust parameters accordingly

**Section sources**
- [faiss_index_manager.py](file://app/utils/faiss_manager/faiss_index_manager.py#L1-L187)
- [ml_data_manager.py](file://app/modules/wb_adv_updater/ml_data_manager.py#L1-L50)
- [Transformers.py](file://app/utils/text_master/Transformers.py#L1-L88)

## Performance Considerations
The system is optimized for large-scale clustering operations with thousands of keywords. Key performance considerations include memory usage, indexing time, and query latency. The implementation uses batch processing, efficient indexing, and caching to handle large datasets.

### Performance Optimization Strategies:
- **Batch processing**: Processes keywords in batches to reduce memory footprint
- **Index persistence**: Saves FAISS indexes to disk to avoid recreation
- **Asynchronous operations**: Uses async/await for I/O operations
- **Memory mapping**: Loads only necessary portions of large indexes
- **Connection pooling**: Reuses database connections for vector retrieval

### Memory Usage Optimization:
- Uses float32 instead of float64 for vector storage
- Implements incremental index building
- Provides options to load only required indexes
- Includes automatic index cleanup and saving

**Section sources**
- [faiss_index_manager.py](file://app/utils/faiss_manager/faiss_index_manager.py#L1-L187)
- [faiss_index.py](file://app/utils/faiss_manager/faiss_index.py#L1-L105)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L1066-L1104)

## Conclusion
The Keyword Clustering sub-feature provides a robust system for semantic keyword grouping using word2vec embeddings and FAISS-based similarity search. The implementation enables effective bid group optimization and campaign structuring through meaningful semantic clusters. By integrating with the ML pipeline, the system supports continuous improvement and adaptation to changing market conditions. With proper tuning and performance optimization, this system can efficiently handle large-scale clustering operations for thousands of keywords while maintaining high-quality cluster formation.