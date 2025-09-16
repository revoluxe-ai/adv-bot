# Campaign Automation

<cite>
**Referenced Files in This Document**   
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [models.py](file://app/modules/wb_adv_updater/models.py)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py)
- [ml_common_funcs.py](file://app/modules/wb_adv_updater/ml_common_funcs.py)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py)
- [data_setter.py](file://app/modules/wb_adv_updater/data_setter.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
The Campaign Automation module is a sophisticated system designed to manage and optimize advertising campaigns on the Wildberries platform. This document focuses on the wb_adv_updater implementation, which serves as the core engine for automated campaign management. The system integrates machine learning for bid optimization, real-time bidding logic, and comprehensive lifecycle management to maximize advertising effectiveness. The architecture is built around key components including ML.py for CTR prediction, bidder.py for dynamic bid adjustments, and runner.py for orchestrating the automation workflow. The system interacts with the Wildberries API through wb_manager.py and maintains state through Redis and ClickHouse databases. This documentation provides a detailed analysis of the domain model, integration patterns, configuration options, error handling mechanisms, and performance characteristics of the campaign automation system.

## Project Structure
The wb_adv_updater module is organized as a comprehensive system for managing advertising campaigns on Wildberries. The structure follows a modular approach with clear separation of concerns between different functional components. The core functionality is implemented in the wb_adv_updater directory, which contains specialized modules for machine learning, bidding, data management, and lifecycle operations. Supporting components include data models, utility functions, and integration layers for external systems like Redis, ClickHouse, and the Wildberries API. The architecture follows a layered pattern with distinct components for data access, business logic, and integration, enabling maintainability and extensibility of the campaign automation system.

```mermaid
graph TD
subgraph "wb_adv_updater Module"
ML[ML.py<br>CTR Prediction & ML]
bidder[bidder.py<br>Bid Optimization]
runner[runner.py<br>Workflow Orchestration]
wb_manager[wb_manager.py<br>Wildberries Integration]
data_manager[data_manager.py<br>Business Logic]
data_getter[data_getter.py<br>Data Access]
data_setter[data_setter.py<br>Data Updates]
fitter[fitter.py<br>Model Training]
models[models.py<br>Data Models]
end
subgraph "External Integrations"
Redis[(Redis<br>Cache & State)]
ClickHouse[(ClickHouse<br>Analytics)]
WildberriesAPI[(Wildberries API<br>Platform Integration)]
end
ML --> data_getter
ML --> data_manager
bidder --> data_manager
bidder --> wb_manager
runner --> wb_manager
runner --> ML
wb_manager --> WildberriesAPI
data_manager --> Redis
data_manager --> ClickHouse
data_getter --> Redis
data_getter --> ClickHouse
data_setter --> WildberriesAPI
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py)
- [runner.py](file://app/modules/wb_adv_updater/runner.py)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)

**Section sources**
- [app/modules/wb_adv_updater](file://app/modules/wb_adv_updater)

## Core Components
The wb_adv_updater module consists of several core components that work together to automate advertising campaign management. The ML.py component implements machine learning functionality for CTR prediction, using XGBoost models trained on historical campaign data. The bidder.py module contains the real-time bidding logic that adjusts CPC bids based on campaign performance and target positions. The runner.py component serves as the orchestration layer, managing the execution of various automation processes. The wb_manager.py module provides integration with the Wildberries API, handling authentication and API requests. The data_manager.py component implements the core business logic for campaign analysis and decision-making, while data_getter.py and data_setter.py handle data access and updates respectively. These components work in concert to create a comprehensive campaign automation system that optimizes advertising performance through data-driven decision making.

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py#L1-L130)
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L96)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L1-L443)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L1810)

## Architecture Overview
The Campaign Automation system follows a modular architecture with clear separation between components responsible for different aspects of campaign management. The system is built around a core automation engine that coordinates various specialized modules for machine learning, bidding, data management, and API integration. The architecture follows a layered pattern with data access components at the foundation, business logic in the middle layer, and integration components at the top. The system leverages Redis for caching and state management, ClickHouse for analytics and historical data storage, and PostgreSQL for persistent configuration data. The workflow is orchestrated through the runner.py component, which manages the execution of various automation processes on a scheduled basis. The architecture is designed for scalability and reliability, with error handling and retry mechanisms built into critical components.

```mermaid
graph TD
subgraph "Orchestration Layer"
runner[runner.py<br>Process Orchestration]
end
subgraph "Core Logic Layer"
ML[ML.py<br>CTR Prediction]
bidder[bidder.py<br>Bid Optimization]
data_manager[data_manager.py<br>Business Logic]
wb_manager[wb_manager.py<br>Wildberries Integration]
end
subgraph "Data Access Layer"
data_getter[data_getter.py<br>Data Retrieval]
data_setter[data_setter.py<br>Data Updates]
fitter[fitter.py<br>Model Training]
end
subgraph "Data Storage"
Redis[(Redis<br>Cache & State)]
ClickHouse[(ClickHouse<br>Analytics)]
PostgreSQL[(PostgreSQL<br>Configuration)]
end
subgraph "External Systems"
WildberriesAPI[(Wildberries API)]
end
runner --> ML
runner --> bidder
runner --> wb_manager
runner --> data_manager
ML --> data_getter
ML --> data_manager
bidder --> data_manager
bidder --> wb_manager
data_manager --> data_getter
data_manager --> data_setter
data_getter --> Redis
data_getter --> ClickHouse
data_getter --> PostgreSQL
data_setter --> Redis
data_setter --> ClickHouse
data_setter --> WildberriesAPI
wb_manager --> WildberriesAPI
```

**Diagram sources**
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L96)
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py#L1-L130)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L1810)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L1-L443)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py#L1-L54)
- [data_setter.py](file://app/modules/wb_adv_updater/data_setter.py#L1-L141)

## Detailed Component Analysis

### ML.py Analysis
The ML.py component implements the machine learning functionality for CTR prediction and model training. It uses XGBoost as the primary machine learning algorithm, with features derived from both item characteristics and keyword attributes. The component includes a Predictor class that loads trained models and generates CTR predictions for keywords, and a Fitter class that handles model training and feature engineering. The system integrates with Redis for feature caching and PostgreSQL for configuration data, creating a comprehensive machine learning pipeline for advertising optimization.

```mermaid
classDiagram
class Predictor {
+_predict(df : DataFrame) DataFrame
+predict_ctr_for_keywords() void
+_get_df_for_predict(adv_settings : List[AdvSetting]) DataFrame
+get_nmid_to_item_features(nmids : str) dict
+get_keyword_features(clear_keywords : List[str]) dict
+__update_predict_ctr(redis_pipeline : Pipeline, keyword_setting : KeywordSetting, predict_df : DataFrame) void
}
class Fitter {
+__get_average_vector(nmids : str, df_vectors : DataFrame) array
+fill_average_vector(df_stat : DataFrame, df_vectors : DataFrame) DataFrame
}
class ML {
+global_model : XGBModel
+update_predict_ctr_process_semaphore : Semaphore
+data_getter : DataGetter
}
Predictor --> Fitter : "uses"
Predictor --> data_getter : "uses"
Predictor --> redis_manager : "uses"
Fitter --> data_getter : "uses"
ML --> Predictor : "contains"
ML --> Fitter : "contains"
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)

### bidder.py Analysis
The bidder.py component implements the real-time bidding logic for campaign optimization. It contains functions for managing bid adjustment processes, with logic to increase or decrease CPC bids based on campaign performance and target positions. The component integrates with the Wildberries API through WBApi to execute bid changes and retrieves campaign data from the database through SQLAlchemy. The bidding strategy is based on monitoring keyword positions and adjusting bids in increments defined by the BIDDER_STEP configuration parameter, with safeguards to prevent bids from exceeding maximum limits.

```mermaid
sequenceDiagram
participant MainLoop as runner.py
participant Bidder as bidder.py
participant DataManager as data_manager.py
participant WBApi as WBApi
participant Database as PostgreSQL
MainLoop->>Bidder : _run_bidder_process()
loop For each active campaign
Database->>Bidder : Query AdvSetting with active bidder
Bidder->>DataManager : get_max_adv_bid(adv_setting)
DataManager-->>Bidder : max_cpm
Bidder->>DataManager : get_good_bad_phrases(adv_setting)
DataManager-->>Bidder : keywords
Bidder->>DataManager : get_cpm(adv_setting, keywords)
DataManager-->>Bidder : fact_cpm
alt If best white keyword exists
DataManager->>Bidder : get_best_keyword(white_keywords)
Bidder->>Bidder : Compare position with max_position
alt position < max_position
Bidder->>Bidder : new_cpm = fact_cpm - step
else position > max_position
Bidder->>Bidder : new_cpm = fact_cpm + step
else
Bidder->>Bidder : new_cpm = fact_cpm
end
end
Bidder->>Bidder : Ensure new_cpm <= max_cpm
Bidder->>Bidder : Ensure new_cpm >= 125
Bidder->>WBApi : update_cpm(adv_id, new_cpm)
alt If search_adv_id exists
Bidder->>WBApi : set_search_cpm(adv_id, new_cpm)
end
end
```

**Diagram sources**
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py#L1-L130)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L1810)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L1-L443)

**Section sources**
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py#L1-L130)

### runner.py Analysis
The runner.py component serves as the orchestration layer for the campaign automation system, managing the execution of various background processes. It contains functions for running periodic tasks such as CTR prediction updates, keyword synchronization with Wildberries, vector updates in Redis and Neo4j, and payment processing for campaigns. The component uses asyncio for concurrent execution of multiple processes and includes error handling and retry mechanisms to ensure reliability. The main_loop function coordinates the execution of these processes, creating a comprehensive automation workflow that runs continuously.

```mermaid
flowchart TD
Start([Start Main Loop]) --> ProcessPayment["process_payment_for_advs()"]
ProcessPayment --> UpdateVectorsRedis["run_update_vectors_in_redis()"]
UpdateVectorsRedis --> UpdateVectorsNeo4j["run_vector_update_in_neo4j()"]
UpdateVectorsNeo4j --> UpdateConfig["update_wb_config_data(client_session)"]
UpdateConfig --> Gather["asyncio.gather()"]
Gather --> Wait["Wait for all tasks to complete"]
Wait --> ErrorCheck{"Error occurred?"}
ErrorCheck --> |Yes| LogError["Log error with exc_info"]
ErrorCheck --> |No| Sleep["await asyncio.sleep(0)"]
LogError --> Sleep
Sleep --> Start
style Start fill:#f9f,stroke:#333
style Gather fill:#ccf,stroke:#333
style ErrorCheck fill:#ffcc00,stroke:#333
```

**Diagram sources**
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L96)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L1-L443)

**Section sources**
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L96)

### wb_manager.py Analysis
The wb_manager.py component provides integration with the Wildberries platform, handling API requests and data synchronization. It contains functions for processing campaign payments, updating keyword vectors in Redis and Neo4j, and synchronizing campaign data with the Wildberries API. The component manages the financial aspects of campaign automation, including balance and bonus payments, and ensures that campaigns remain active by processing daily payments. It also handles the vectorization of keywords and items, updating these representations in both Redis and Neo4j for use in machine learning models.

```mermaid
classDiagram
class wb_manager {
+get_count_advs_for_wb_cabinet(wb_cabinet : WBCabinet, adv_settings : List[AdvSetting]) int
+check_adv_payment(session : AsyncSession, adv_setting : AdvSetting, current_date : date) bool
+process_payment_for_advs() void
+graph_vector_update() void
+update_vectors_update_in_graph() void
+update_vectors_in_redis() void
+insert_or_update_keywords(keyword_stats : List[KeywordStat], adv_id : int, table_name : str) void
+update_keywords_stat_in_click_house(keyword_stats : List[KeywordStat], adv_id : int, table_name : str) void
}
class DataScience {
+update_vectors_in_redis() void
+get_nmid_vectors(nmids_batch : Set[int]) List[Tuple[int, List[float]]]
+get_keywords_vectors_by_keywords(keywords : List[str]) List[Tuple[str, List[float]]]
}
class Pricer {
+get_price_for_day_for_shop(shop_id : str) float
}
class WBApi {
+advert.update_cpm(adv_id : int, cpm : float) void
+advert.set_minus_phrases(adv_setting : AdvSetting, bad_phrases : List[str]) void
}
wb_manager --> DataScience : "uses"
wb_manager --> Pricer : "uses"
wb_manager --> WBApi : "uses"
wb_manager --> redis_manager : "uses"
wb_manager --> clickhouse_client : "uses"
```

**Diagram sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L1-L443)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L1810)
- [models.py](file://app/modules/wb_adv_updater/models.py#L1-L58)

**Section sources**
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L1-L443)

### data_manager.py Analysis
The data_manager.py component implements the core business logic for campaign analysis and decision-making. It contains functions for retrieving and processing campaign data from various sources, including ClickHouse for historical statistics and Redis for real-time data. The component handles the calculation of key metrics such as CTR, CPC, and campaign performance, and implements logic for determining which keywords should be included or excluded from campaigns. It also manages the conversion of individual keywords into clusters for more effective campaign management and provides utilities for working with campaign data across the system.

```mermaid
flowchart TD
Start([Start get_good_bad_phrases]) --> GetMinCTR["get_min_ctr(adv_setting)"]
GetMinCTR --> GetKeywordStats["get_keywords_statistic_clickhouse(adv_setting)"]
GetKeywordStats --> CheckClusters{"clusters_mode?"}
CheckClusters --> |Yes| ConvertClusters["convert_keyword_stats_in_clusters(keyword_stats)"]
CheckClusters --> |No| Continue
ConvertClusters --> Continue
Continue --> SetPositions["set_positions(keyword_stats, adv_setting)"]
SetPositions --> GetPredictCTR["redis_manager.get_adv_id_to_text_predict_ctr_dict(adv_id, texts)"]
GetPredictCTR --> GetCPM["get_cpm(adv_setting, keyword_stats)"]
GetCPM --> ProcessKeywords["For each keyword_stat"]
ProcessKeywords --> SetPredictCTR["__set_predict_ctr(keyword_stats, min_ctr, adv_setting)"]
SetPredictCTR --> CheckMaxPosition{"max_position?"}
CheckMaxPosition --> |Yes| CheckOrganicPosition{"organic_position <= max_position?"}
CheckOrganicPosition --> |Yes| SetBadStatus["status = BAD, reason = 'max_position'"]
CheckOrganicPosition --> |No| CheckMaxCPC{"max_cpc?"}
CheckMaxPosition --> |No| CheckMaxCPC
CheckMaxCPC --> |Yes| CalculateCPC["Calculate CPC from cpm_now and predict_ctr"]
CalculateCPC --> |cpc > max_cpc| SetBadStatusCPC["status = BAD, reason = 'max_cpc'"]
CheckMaxCPC --> |No| CheckViews{"views < min_views_for_ml_predict?"}
CheckViews --> |Yes| SetGoodStatusViews["status = GOOD, reason = 'VIEWS_IS_NOT_ENOUGH'"]
CheckViews --> |No| CheckHardStatus{"hard_status?"}
CheckHardStatus --> |3| SetBadStatusHard["status = BAD, reason = 'turn_off'"]
CheckHardStatus --> |2| SetGoodStatusWhite["status = GOOD, reason = 'white_list'"]
CheckHardStatus --> |0| SetBadStatusBlack["status = BAD, reason = 'black_list'"]
CheckHardStatus --> |Other| CheckMinCTR{"baes_predict_ctr >= min_ctr?"}
CheckMinCTR --> |Yes| SetGoodStatusCTR["status = GOOD, reason = 'baes_ctr_more_than_min_ctr'"]
CheckMinCTR --> |No| SetBadStatusMinCTR["status = BAD, reason = 'min_ctr'"]
SetBadStatus --> End
SetBadStatusCPC --> End
SetGoodStatusViews --> End
SetBadStatusHard --> End
SetGoodStatusWhite --> End
SetBadStatusBlack --> End
SetGoodStatusCTR --> End
SetBadStatusMinCTR --> End
style Start fill:#f9f,stroke:#333
style End fill:#f9f,stroke:#333
```

**Diagram sources**
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L1810)
- [redis_manager.py](file://app/core/redis_manager/base_redis_manager.py#L1-L50)
- [clickhouse_client.py](file://app/utils/click_house/client.py#L1-L50)

**Section sources**
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L1810)

## Dependency Analysis
The wb_adv_updater module has a well-defined dependency structure that enables modularity and separation of concerns. The core components depend on utility modules for data access and external integrations, while maintaining loose coupling between functional areas. The ML.py component depends on data_getter.py for feature retrieval and data_manager.py for campaign data, while bidder.py depends on data_manager.py for campaign analysis and wb_manager.py for API integration. The runner.py component orchestrates the execution of other components, creating a dependency on ML.py, wb_manager.py, and other modules. Data access components like data_getter.py and data_setter.py depend on external systems like Redis, ClickHouse, and the Wildberries API, while business logic components depend on data models defined in models.py. This dependency structure enables independent development and testing of components while maintaining a cohesive system architecture.

```mermaid
graph TD
ML[ML.py] --> data_getter[data_getter.py]
ML --> data_manager[data_manager.py]
ML --> redis_manager[redis_manager]
ML --> models[models.py]
bidder[bidder.py] --> data_manager[data_manager.py]
bidder --> wb_manager[wb_manager.py]
bidder --> WBApi[WBApi]
bidder --> models[models.py]
runner[runner.py] --> wb_manager[wb_manager.py]
runner --> ML[ML.py]
runner --> data_manager[data_manager.py]
runner --> models[models.py]
wb_manager[wb_manager.py] --> WBApi[WBApi]
wb_manager --> redis_manager[redis_manager]
wb_manager --> clickhouse_client[clickhouse_client]
wb_manager --> models[models.py]
wb_manager --> DataScience[DataScience]
wb_manager --> Pricer[Pricer]
data_manager[data_manager.py] --> redis_manager[redis_manager]
data_manager[data_manager.py] --> clickhouse_client[clickhouse_client]
data_manager[data_manager.py] --> models[models.py]
data_getter[data_getter.py] --> redis_manager[redis_manager]
data_getter[data_getter.py] --> clickhouse_client[clickhouse_client]
data_getter[data_getter.py] --> DataScience[DataScience]
data_setter[data_setter.py] --> WBApi[WBApi]
data_setter[data_setter.py] --> redis_manager[redis_manager]
data_setter[data_setter.py] --> clickhouse_client[clickhouse_client]
fitter[fitter.py] --> data_getter[data_getter.py]
fitter[fitter.py] --> data_manager[data_manager.py]
fitter[fitter.py] --> models[models.py]
```

**Diagram sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py#L1-L130)
- [runner.py](file://app/modules/wb_adv_updater/runner.py#L1-L96)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L1-L443)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L1810)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py#L1-L54)
- [data_setter.py](file://app/modules/wb_adv_updater/data_setter.py#L1-L141)
- [fitter.py](file://app/modules/wb_adv_updater/fitter.py#L1-L282)

**Section sources**
- [app/modules/wb_adv_updater](file://app/modules/wb_adv_updater)

## Performance Considerations
The wb_adv_updater system is designed with performance and scalability in mind, particularly given the high-frequency nature of advertising campaign updates. The system leverages Redis for caching frequently accessed data such as keyword vectors and campaign statistics, reducing database load and improving response times. ClickHouse is used for analytics and historical data storage, providing fast query performance for large datasets. The system uses asyncio for concurrent execution of multiple processes, enabling efficient use of system resources. The ML.py component uses threading for CPU-intensive operations like model prediction and training, preventing these operations from blocking the event loop. The bidder.py component implements rate limiting and error handling to prevent overwhelming the Wildberries API with requests. The data_manager.py component includes optimizations for batch processing of campaign data, reducing the number of database queries required for analysis. These performance considerations ensure that the system can handle the demands of real-time campaign optimization at scale.

**Section sources**
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py#L1-L130)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L1810)
- [data_getter.py](file://app/modules/wb_adv_updater/data_getter.py#L1-L54)

## Troubleshooting Guide
The wb_adv_updater system includes comprehensive error handling and logging to facilitate troubleshooting of common issues. When encountering problems with campaign automation, the first step is to check the application logs for error messages and stack traces. Common issues include rate limiting by the Wildberries API, insufficient campaign budgets, and model prediction failures. For rate limiting issues, the system implements retry mechanisms with exponential backoff, but persistent issues may require adjusting the frequency of API requests. Budget exhaustion can be addressed by ensuring sufficient funds are available in the associated Wildberries cabinet or by adjusting campaign spending limits. Model prediction failures may occur due to missing feature data or model loading issues, which can be resolved by verifying the integrity of the model file and feature data in Redis. When troubleshooting, it's important to examine the specific error messages and context to identify the root cause and apply the appropriate solution.

**Section sources**
- [bidder.py](file://app/modules/wb_adv_updater/bidder.py#L1-L130)
- [wb_manager.py](file://app/modules/wb_adv_updater/wb_manager.py#L1-L443)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L1810)
- [ML.py](file://app/modules/wb_adv_updater/ML.py#L1-L257)

## Conclusion
The wb_adv_updater module provides a comprehensive solution for automated campaign management on the Wildberries platform. By integrating machine learning for CTR prediction, real-time bidding logic, and comprehensive lifecycle management, the system enables data-driven optimization of advertising campaigns. The modular architecture with clear separation of concerns facilitates maintainability and extensibility, while the use of Redis, ClickHouse, and PostgreSQL provides a robust data management foundation. The system's design considerations for performance, reliability, and error handling ensure that it can operate effectively in a production environment. Future enhancements could include more sophisticated machine learning models, additional optimization strategies, and expanded integration with other advertising platforms. Overall, the wb_adv_updater module represents a sophisticated and effective solution for automating and optimizing advertising campaigns.