# Neo4j Graph Model

<cite>
**Referenced Files in This Document**   
- [driver.py](file://app/utils/NeoDataScience/driver.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [__init__.py](file://app/utils/redis_manager/__init__.py)
- [namedtuples.py](file://app/modules/common_slaves/wildberries/data_classes/namedtuples.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Node Types](#node-types)
3. [Relationship Types](#relationship-types)
4. [Data Transformation Process](#data-transformation-process)
5. [Cypher Query Patterns](#cypher-query-patterns)
6. [Data Synchronization](#data-synchronization)
7. [Performance Considerations](#performance-considerations)
8. [Use Cases](#use-cases)
9. [Conclusion](#conclusion)

## Introduction
The Neo4j graph model in the adv-bot system represents keyword relationships and clustering for Wildberries advertising optimization. This documentation details the graph structure, data flow, and operational patterns used to analyze keyword co-occurrence data from search logs. The system transforms raw search data into a knowledge graph that enables relevance filtering, clustering, and semantic analysis of keywords. The graph model connects keywords, products, and categories through various relationship types, allowing for sophisticated analysis of search behavior and product relevance.

## Node Types
The Neo4j graph model implements several node types to represent entities in the advertising ecosystem. The primary node types include Keyword, Product (represented as Item), and Category (WbCategory), along with supporting nodes for images, brands, and characteristics.

The Keyword node represents individual search terms used by customers on Wildberries. Each Keyword node contains text and word2vec properties, where word2vec stores the vector representation of the keyword for semantic similarity calculations. Keyword nodes are connected to KeywordPhrase nodes through IS relationships, representing the composition of multi-word phrases.

The Item node represents products available on Wildberries, identified by their nmids and offer_ids. Item nodes contain fastrp properties that store vector embeddings generated through graph algorithms. These embeddings capture the semantic characteristics of products based on their relationships with keywords and images.

Additional node types include Image nodes that represent product images with vgg19 vector properties, Brand nodes for product brands, WBChar nodes for product characteristics, and WbCategory nodes for product categories. These nodes form a rich network that connects products to their attributes and customer search behavior.

**Section sources**
- [driver.py](file://app/utils/NeoDataScience/driver.py#L627-L672)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L83-L130)
- [namedtuples.py](file://app/modules/common_slaves/wildberries/data_classes/namedtuples.py#L0-L20)

## Relationship Types
The graph model implements several relationship types to capture different kinds of connections between nodes. The primary relationship types are IS, LIKE, and IN, each serving a specific purpose in representing the semantic and structural relationships within the data.

The IS relationship connects KeywordPhrase nodes to their constituent Keyword nodes, representing the composition of multi-word search phrases. This relationship has a dist property that represents the distribution weight, calculated as the inverse of the number of words in the phrase. The IS relationship also connects items to images and keywords to images, establishing the fundamental associations between products and search terms.

The LIKE relationship represents semantic similarity between nodes, particularly between keywords. These relationships are created using the Graph Data Science library's KNN (k-nearest neighbors) algorithm, which calculates similarity based on vector embeddings. The LIKE relationship has a dist property that stores the similarity score, with higher values indicating greater semantic similarity.

The IN relationship connects Image nodes to Item nodes, representing the association between product images and the products themselves. This relationship enables image-based product recommendations and similarity calculations. Additional relationship types include DIRECT_DIST for shortest path calculations and KNN for item similarity based on graph embeddings.

**Section sources**
- [driver.py](file://app/utils/NeoDataScience/driver.py#L627-L672)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L237-L293)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L461-L499)

## Data Transformation Process
The data transformation process converts keyword co-occurrence data from Wildberries search logs into a structured knowledge graph in Neo4j. This process begins with raw search log data that captures customer search behavior, including the keywords used and the products viewed or purchased.

The transformation pipeline first processes keyword phrases by breaking them down into individual keywords and calculating vector representations using word2vec models. The add_keyword_phrase method in the DataScience class handles this process, creating KeywordPhrase nodes and connecting them to individual Keyword nodes through IS relationships. The dist property on these relationships is set based on the number of words in the phrase.

Vector embeddings are then calculated for both keywords and products using the Fast Random Projection (FastRP) algorithm from the Neo4j Graph Data Science library. The create_base_graph method establishes the initial graph structure, while the fit_fastrp method generates embeddings by considering the graph topology and relationship weights. These embeddings capture the semantic meaning of keywords and products in a multi-dimensional space.

The final step involves creating semantic similarity relationships between nodes using the KNN algorithm. The linking_keywords method creates a temporary subgraph of keywords with word2vec properties, applies the KNN algorithm to find semantically similar keywords, and establishes LIKE relationships between them. This process transforms the raw co-occurrence data into a rich knowledge graph that captures both explicit associations and implicit semantic relationships.

**Section sources**
- [driver.py](file://app/utils/NeoDataScience/driver.py#L703-L742)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L433-L463)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L842-L880)

## Cypher Query Patterns
The system employs several Cypher query patterns to extract insights from the graph model, focusing on finding semantically related keywords and identifying high-performing keyword clusters. These queries leverage the graph structure and vector embeddings to provide actionable insights for advertising optimization.

For finding semantically related keywords, the system uses KNN-based queries that traverse LIKE relationships between Keyword nodes. The get_knn method demonstrates this pattern, retrieving the nearest neighbors of a given item based on their vector embeddings. Similarly, the get_near_offer_ids_by_keyword method finds products associated with a specific keyword by traversing the graph from Keyword to Image to Item nodes, using relationship distances to rank results.

To identify high-performing keyword clusters, the system employs community detection algorithms through the gds.kmeans.stream procedure. The get_k_mean_groups method executes this pattern, applying k-means clustering to nodes based on their fastrp vector properties. This identifies natural groupings of products or keywords that share similar characteristics, which can be used to create targeted advertising campaigns.

The system also uses pathfinding queries to calculate direct distances between items and keywords. The set_direct_dist_item_to_keywords method employs the gds.allShortestPaths.delta.write procedure to compute shortest paths between Item and Keyword nodes, creating DIRECT_DIST relationships that capture the strength of association. These pre-computed distances enable fast retrieval of relevant keywords for any given product.

**Section sources**
- [driver.py](file://app/utils/NeoDataScience/driver.py#L83-L130)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L529-L565)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L205-L240)

## Data Synchronization
The data synchronization process maintains consistency between Neo4j, Redis, and PostgreSQL, ensuring that the graph model reflects the latest data from various sources. This process involves both batch updates and real-time ingestion mechanisms to keep the knowledge graph current.

The synchronization from PostgreSQL to Neo4j occurs through periodic batch updates that extract keyword statistics and product data from the relational database. The data_manager module handles this process, retrieving keyword data from ClickHouse and transforming it into the format required for Neo4j ingestion. The update_keywords_vectors_process method coordinates this flow, fetching recent keywords and updating their vector representations in the graph.

For Redis to Neo4j synchronization, the system uses a push-based model where vector updates are propagated from Redis to Neo4j. The _update_keywords_vectors_in_redis method queries Neo4j for keywords with valid fastrp embeddings and writes these vectors to Redis using the set_keyword_vector function. This ensures that frequently accessed vector data is available in the low-latency Redis cache.

Real-time ingestion is handled through event-driven updates triggered by changes in product data or keyword performance. The system monitors Wildberries API for updates to product catalogs and search trends, processing these changes through the keyword_sending_to_neo4j.py script. This script transforms new keyword data into the appropriate format and ingests it into Neo4j, maintaining the freshness of the knowledge graph.

**Section sources**
- [driver.py](file://app/utils/NeoDataScience/driver.py#L1211-L1244)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L1242-L1278)
- [__init__.py](file://app/utils/redis_manager/__init__.py#L342-L384)

## Performance Considerations
The system implements several performance optimizations for graph traversals and indexing to handle the scale of Wildberries' product catalog and search data. These optimizations focus on efficient vector calculations, relationship weighting, and query execution patterns.

Indexing strategies are applied to keyword text and product IDs to accelerate lookup operations. The graph model uses composite indexes on node properties such as text for Keyword nodes and nmid for Item nodes. These indexes enable fast retrieval of specific nodes during query execution, reducing the need for full graph scans.

For graph traversals, the system employs subgraph projection through the GDS library to limit the scope of computationally intensive operations. The create_base_graph method defines a filtered graph projection that includes only relevant node labels and relationship types, reducing memory usage and computation time. This approach allows the system to perform vector calculations and similarity searches on focused subsets of the graph.

The relationship weighting system optimizes traversal performance by normalizing relationship distances. The set_dist_on_null_rels method and its variants calculate normalized distances for IS relationships based on the frequency of associations between entities. This normalization ensures that traversal algorithms can accurately weigh the strength of relationships without being skewed by highly connected nodes.

Memory management is addressed through batch processing and incremental updates. The system processes large datasets in batches to avoid memory overflow, particularly during vector embedding calculations. The use of asynchronous methods in the DataScience class enables non-blocking operations, allowing the system to handle multiple update requests concurrently without degrading performance.

**Section sources**
- [driver.py](file://app/utils/NeoDataScience/driver.py#L205-L240)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L83-L130)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L627-L672)

## Use Cases
The Neo4j graph model supports several key use cases for advertising optimization on Wildberries, including keyword set expansion and emerging trend detection. These use cases leverage the semantic relationships and clustering capabilities of the knowledge graph to improve advertising performance.

For keyword set expansion, the system uses the graph's semantic similarity relationships to identify related keywords that can be added to advertising campaigns. By traversing LIKE relationships between Keyword nodes, the system can suggest semantically similar terms that customers might use to find similar products. The get_near_offer_ids_by_keyword method demonstrates this capability, finding products associated with a keyword through multi-hop traversals that capture indirect relationships.

Emerging trend detection is accomplished through analysis of keyword co-occurrence patterns and clustering. The system monitors changes in keyword relationships over time, identifying clusters of keywords that are gaining popularity. The get_k_mean_groups method enables this analysis by applying k-means clustering to keyword vectors, revealing natural groupings that may represent emerging product categories or customer interests.

The graph model also supports competitive analysis by identifying keyword gaps in advertising campaigns. By comparing the keyword clusters associated with a merchant's products to those of competitors, the system can identify high-potential keywords that are being overlooked. This analysis is facilitated by the DIRECT_DIST relationships, which quantify the strength of association between products and keywords, allowing for precise measurement of keyword coverage.

**Section sources**
- [driver.py](file://app/utils/NeoDataScience/driver.py#L529-L565)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L293-L336)
- [driver.py](file://app/utils/NeoDataScience/driver.py#L83-L130)

## Conclusion
The Neo4j graph model in the adv-bot system provides a sophisticated framework for analyzing keyword relationships and clustering in the context of Wildberries advertising. By transforming search log data into a knowledge graph, the system enables advanced semantic analysis that goes beyond simple keyword matching. The integration of vector embeddings and graph algorithms allows for the identification of semantically related keywords and natural product clusters, providing valuable insights for advertising optimization.

The system's architecture effectively combines batch processing with real-time ingestion to maintain a current and comprehensive view of customer search behavior. The synchronization between Neo4j, Redis, and PostgreSQL ensures that performance-critical data is available where needed, while the graph model preserves the rich relationships between entities. Performance optimizations such as subgraph projection and relationship weighting enable efficient processing of large-scale data.

Future enhancements could include incorporating temporal analysis to track the evolution of keyword relationships over time, or expanding the feature set to include customer segmentation based on search behavior. The existing foundation provides a robust platform for these and other advanced analytics capabilities that can further improve advertising effectiveness on the Wildberries platform.