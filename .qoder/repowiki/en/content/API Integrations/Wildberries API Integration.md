# Wildberries API Integration

<cite>
**Referenced Files in This Document**   
- [base.py](file://app/core/wb_api/base.py)
- [http_request.py](file://app/core/wb_api/http_request.py)
- [adv_rights_checker.py](file://app/core/wb_api/mixins/adv_rights_checker.py)
- [check_righter.py](file://app/core/wb_api/check_righter.py)
- [adv.py](file://app/core/wb_api/data_classes/adv.py)
- [adv_stat_classes.py](file://app/core/wb_api/data_classes/adv_stat_classes.py)
- [wb_api.py](file://app/client_bot/user_interface/handlers/start/wb_api.py)
- [wb_api.py](file://app/modules/shop_runner/modules/wb_api/wb_api.py)
- [wb_api.py](file://app/modules/shop_runner/bidder/wb_api.py)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py)
- [super_cabinet_manager.py](file://app/modules/common_slaves/wildberries/super_cabinet_manager.py)
- [ABC_WB_API.py](file://app/modules/common_slaves/wildberries/ABC_WB_API.py)
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py)
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
This document provides comprehensive documentation for the Wildberries API integration layer used in the advertising management system. The system enables automated management of advertising campaigns, keyword statistics, product data retrieval, and shop configuration through the Wildberries marketplace API. The integration layer handles authentication, rate limiting, error handling, and provides a robust foundation for various modules including client_bot, shop_runner, and bidder functionality. The documentation covers the core WBAPI class implementation, authentication mechanisms, endpoint usage patterns, and best practices for working with the Wildberries API ecosystem.

## Project Structure
The Wildberries API integration is organized within the app/core/wb_api directory, with supporting components distributed across various modules. The core API functionality is implemented in the base.py file, which contains the BaseAPI class that serves as the foundation for all Wildberries API interactions. The mixins directory contains specialized functionality for different API domains such as advertising, content, and statistics. Data classes are defined in the data_classes directory to represent API responses and request payloads. Various modules like client_bot and shop_runner implement their own API clients by inheriting from the base classes and adding module-specific functionality.

```mermaid
graph TD
subgraph "Core API Layer"
base[base.py]
http_request[http_request.py]
exceptions[exceptions.py]
protocols[protocols.py]
end
subgraph "Mixins"
adv_mixin[adv.py]
content_mixin[content.py]
statistic_mixin[statistic_mixin.py]
adv_rights_checker[adv_rights_checker.py]
end
subgraph "Data Classes"
adv_data[adv.py]
keywordstat[keywordstat.py]
adv_stat_classes[adv_stat_classes.py]
end
subgraph "Module Implementations"
client_bot_wb_api[client_bot/wb_api.py]
shop_runner_wb_api[shop_runner/wb_api.py]
bidder_wb_api[bidder/wb_api.py]
end
base --> mixins
base --> data_classes
mixins --> module_implementations
data_classes --> module_implementations
```

**Diagram sources**
- [base.py](file://app/core/wb_api/base.py)
- [adv.py](file://app/core/wb_api/mixins/adv.py)
- [adv_stat_classes.py](file://app/core/wb_api/data_classes/adv_stat_classes.py)

**Section sources**
- [base.py](file://app/core/wb_api/base.py)
- [http_request.py](file://app/core/wb_api/http_request.py)

## Core Components
The Wildberries API integration is built around several core components that provide the foundation for all API interactions. The BaseAPI class serves as the primary interface for making requests to the Wildberries API, handling authentication, token management, and request execution. The http_request.py module provides the underlying HTTP request functionality with retry logic and error handling. The adv_rights_checker mixin enables permission validation for API access. Data classes such as Adv and Statistic provide structured representations of API responses. The implementation supports multiple inheritance, allowing modules to combine different mixins based on their specific requirements.

**Section sources**
- [base.py](file://app/core/wb_api/base.py#L32-L70)
- [http_request.py](file://app/core/wb_api/http_request.py#L0-L213)
- [adv_rights_checker.py](file://app/core/wb_api/mixins/adv_rights_checker.py#L0-L6)

## Architecture Overview
The Wildberries API integration follows a modular architecture with a clear separation of concerns. At the core is the BaseAPI class, which handles authentication, token management, and basic request execution. This class is extended through mixins that provide domain-specific functionality for advertising, content, and statistics. Different modules create their own API clients by inheriting from BaseAPI and the appropriate mixins. The architecture supports multiple tokens per shop, automatic token rotation when permissions are insufficient, and comprehensive error handling. The system integrates with Redis for caching and state management, and uses SQLAlchemy for persistent storage of configuration and state data.

```mermaid
graph TD
Client["Client Application"]
API["Wildberries API Integration Layer"]
Wildberries["Wildberries API"]
subgraph "Integration Layer"
BaseAPI["BaseAPI"]
Mixins["Mixins"]
DataClasses["Data Classes"]
HTTPClient["HTTP Client"]
end
Client --> API
API --> Wildberries
BaseAPI --> Mixins
BaseAPI --> DataClasses
BaseAPI --> HTTPClient
Mixins --> HTTPClient
DataClasses --> HTTPClient
HTTPClient --> |Requests| Wildberries
Wildberries --> |Responses| HTTPClient
style BaseAPI fill:#f9f,stroke:#333
style Mixins fill:#bbf,stroke:#333
style DataClasses fill:#f96,stroke:#333
style HTTPClient fill:#9f9,stroke:#333
```

**Diagram sources**
- [base.py](file://app/core/wb_api/base.py#L32-L115)
- [http_request.py](file://app/core/wb_api/http_request.py#L0-L213)
- [adv.py](file://app/core/wb_api/mixins/adv.py)

## Detailed Component Analysis

### Base API Implementation
The BaseAPI class provides the foundational functionality for all Wildberries API interactions. It manages authentication through WBToken headers, handles multiple tokens per shop, and implements automatic token rotation when necessary. The class maintains state for API call rates and implements retry logic for failed requests. It also provides utility methods for chunking large requests to comply with API limitations.

```mermaid
classDiagram
class BaseAPI {
+str HOST
+__init__(wb_access : WBCabinetAccess, client_session : ClientSession)
+property headers : Headers
+property shop_id : str
+static chunks(lst : list[T], n : int) Generator[list[T], None, None]
+async set_next_token(method_name : str) None
}
class Headers {
+__init__(token : WBToken)
+property standart : dict[str, str]
}
BaseAPI --> Headers : "uses"
BaseAPI --> WBCabinetAccess : "depends on"
BaseAPI --> WBToken : "uses"
```

**Diagram sources**
- [base.py](file://app/core/wb_api/base.py#L32-L115)
- [ABC_WB_API.py](file://app/modules/common_slaves/wildberries/ABC_WB_API.py#L0-L115)

**Section sources**
- [base.py](file://app/core/wb_api/base.py#L32-L115)
- [super_cabinet_manager.py](file://app/modules/common_slaves/wildberries/super_cabinet_manager.py#L0-L46)

### Authentication and Token Management
The system implements a robust authentication mechanism using WBToken headers for API requests. Tokens are managed through the WBToken model, which includes validation of token expiration and permissions. The integration supports multiple tokens per shop, allowing for failover when a token becomes invalid. The AdvRightsChecker mixin provides functionality to validate token permissions for specific API endpoints, ensuring that operations are only attempted when the necessary permissions are present.

```mermaid
sequenceDiagram
participant Client as "Client Module"
participant BaseAPI as "BaseAPI"
participant Headers as "Headers"
participant Token as "WBToken"
Client->>BaseAPI : Initialize with WBCabinetAccess
BaseAPI->>Token : Get tokens from WBCabinetAccess
BaseAPI->>Token : Sort by expiration (newest first)
BaseAPI->>Headers : Create Headers with current token
BaseAPI->>BaseAPI : Store tokens in _free_tokens
BaseAPI->>BaseAPI : Set _current_token to first token
BaseAPI-->>Client : Ready for API calls
Note over BaseAPI,Headers : Token rotation occurs automatically when API calls fail due to permission issues
```

**Diagram sources**
- [base.py](file://app/core/wb_api/base.py#L32-L115)
- [adv_rights_checker.py](file://app/core/wb_api/mixins/adv_rights_checker.py#L0-L6)
- [check_righter.py](file://app/core/wb_api/check_righter.py#L0-L59)

**Section sources**
- [base.py](file://app/core/wb_api/base.py#L32-L115)
- [adv_rights_checker.py](file://app/core/wb_api/mixins/adv_rights_checker.py#L0-L6)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L0-L719)

### Request Handling and Retry Logic
The http_request.py module implements comprehensive request handling with built-in retry logic and rate limiting. The try_except_decorator function provides adaptive retry behavior with exponential backoff, automatically adjusting pause times between requests based on success or failure. The requests function handles HTTP communication, error parsing, and response validation. The system distinguishes between different error types, including rate limiting (TooManyRequests), authentication issues (ApiForbiddenError), and validation errors (BadRequestError).

```mermaid
flowchart TD
Start([Start Request]) --> CheckState["Check API call state"]
CheckState --> LastQuery["Get last query time"]
LastQuery --> WaitTime["Calculate wait time"]
WaitTime --> ShouldWait{"Wait needed?"}
ShouldWait --> |Yes| Wait["Wait required time"]
ShouldWait --> |No| Execute["Execute request"]
Wait --> Execute
Execute --> Success{"Request successful?"}
Success --> |Yes| UpdateState["Update success state"]
Success --> |No| HandleError["Handle error"]
UpdateState --> ReturnResult["Return result"]
HandleError --> IsForbidden{"Error is ApiForbiddenError?"}
IsForbidden --> |Yes| NextToken["Set next token"]
IsForbidden --> |No| IsRateLimit{"Error is TooManyRequests?"}
IsRateLimit --> |Yes| IncreasePause["Double pause time"]
IsRateLimit --> |No| IsMaxAttempts{"Max attempts reached?"}
IsMaxAttempts --> |Yes| ThrowMaxAttempts["Throw MaxAttemptsError"]
IsMaxAttempts --> |No| IncreaseAttempts["Increase attempt count"]
IncreaseAttempts --> Wait
NextToken --> Wait
IncreasePause --> Wait
ThrowMaxAttempts --> ReturnError["Return error"]
ReturnResult --> End([End])
ReturnError --> End
```

**Diagram sources**
- [http_request.py](file://app/core/wb_api/http_request.py#L0-L213)

**Section sources**
- [http_request.py](file://app/core/wb_api/http_request.py#L0-L213)

### Advertising Data Models
The system defines comprehensive data models for representing advertising campaigns and their statistics. The Adv class provides a rich interface for accessing campaign properties, including status, budget, and performance metrics. The Statistic class encapsulates campaign performance data such as views, clicks, CTR, and spending. These models abstract the underlying JSON responses from the Wildberries API, providing a clean, type-safe interface for consuming code.

```mermaid
classDiagram
class Adv {
+__repr__()
+__init__(data)
+property category_name : str
+property subject_id : int
+property adv_type : int
+property status_native : str
+property status_native_ru : str
+property advertId : int
+property changeTime : str
+property createTime : str
+property dailyBudget : int
+property endTime : str
+property name : str
+property startTime : str
+property status : int
+property type : int
+property cpm : int
+property data : dict
+property active : Active
+property nmids : list[int]
}
class Statistic {
+__init__(data)
+property advert_id : int
+property begin : str
+property end : str
+property days : list
+property views : int
+property clicks : int
+property ctr : float
+property cpc : float
+property sum : float
+property atbs : int
+property orders : int
+property cr : float
+property in_shks : int
+property sum_price : float
}
class SimpleStat {
+__init__(data)
+property clicks : int
+property cpc : float
+property ctr : float
+property views : int
+property spend : float
}
Adv --> SimpleStat : "contains"
Statistic --> SimpleStat : "extends"
```

**Diagram sources**
- [adv.py](file://app/core/wb_api/data_classes/adv.py#L0-L250)
- [adv_stat_classes.py](file://app/core/wb_api/data_classes/adv_stat_classes.py#L0-L24)

**Section sources**
- [adv.py](file://app/core/wb_api/data_classes/adv.py#L0-L250)
- [adv_stat_classes.py](file://app/core/wb_api/data_classes/adv_stat_classes.py#L0-L24)

### Module-Specific API Clients
Different modules in the system implement their own API clients by inheriting from BaseAPI and combining appropriate mixins. The client_bot module uses a client with advertising and content functionality. The shop_runner module extends this with statistical capabilities. The bidder module focuses on advertising functionality for bid management. This modular approach allows each component to have precisely the functionality it needs without unnecessary dependencies.

```mermaid
classDiagram
class BaseAPI {
+__init__(wb_access, client_session)
+headers
+shop_id
+chunks()
+set_next_token()
}
class AdvMixin {
+get_active_adv()
+change_cpm()
+stop_adv()
+start_adv()
}
class ContentMixin {
+get_cards_by_token()
+get_cards_filter()
}
class CommonStatMinix {
+get_stat_v2()
+get_stat_v1()
+get_keyword_stat()
}
class ClientBotWBApi {
+Inherits from BaseAPI
+Uses AdvMixin
+Uses ContentMixin
}
class ShopRunnerWBApi {
+Inherits from BaseAPI
+Uses AdvMixin
+Uses ContentMixin
+Uses CommonStatMinix
}
class BidderWBApi {
+Inherits from BaseAPI
+Uses AdvMixin
}
BaseAPI <|-- ClientBotWBApi
BaseAPI <|-- ShopRunnerWBApi
BaseAPI <|-- BidderWBApi
ClientBotWBApi ..> AdvMixin : "uses"
ClientBotWBApi ..> ContentMixin : "uses"
ShopRunnerWBApi ..> AdvMixin : "uses"
ShopRunnerWBApi ..> ContentMixin : "uses"
ShopRunnerWBApi ..> CommonStatMinix : "uses"
BidderWBApi ..> AdvMixin : "uses"
```

**Diagram sources**
- [wb_api.py](file://app/client_bot/user_interface/handlers/start/wb_api.py#L0-L8)
- [wb_api.py](file://app/modules/shop_runner/modules/wb_api/wb_api.py#L0-L9)
- [wb_api.py](file://app/modules/shop_runner/bidder/wb_api.py#L0-L10)

**Section sources**
- [wb_api.py](file://app/client_bot/user_interface/handlers/start/wb_api.py#L0-L8)
- [wb_api.py](file://app/modules/shop_runner/modules/wb_api/wb_api.py#L0-L9)
- [wb_api.py](file://app/modules/shop_runner/bidder/wb_api.py#L0-L10)

## Dependency Analysis
The Wildberries API integration has a well-defined dependency structure that enables modularity and code reuse. The core dependency is on aiohttp for HTTP communication, which is abstracted through the http_request.py module. The system depends on SQLAlchemy for database operations and token management. Pydantic is used for data validation in the data classes. The architecture shows a clear pattern of inheritance and composition, with the BaseAPI class serving as the foundation and mixins providing additional functionality. There is a notable duplication between BaseAPI and ABC_WB_API, which represents a technical debt that should be addressed through refactoring.

```mermaid
graph TD
BaseAPI["BaseAPI"]
HTTPRequest["http_request.py"]
Exceptions["exceptions.py"]
Protocols["protocols.py"]
AdvMixin["adv.py"]
ContentMixin["content.py"]
StatisticMixin["statistic_mixin.py"]
AdvRightsChecker["adv_rights_checker.py"]
CheckRighter["check_righter.py"]
AdvData["adv.py"]
AdvStatClasses["adv_stat_classes.py"]
ClientBotWBApi["client_bot/wb_api.py"]
ShopRunnerWBApi["shop_runner/wb_api.py"]
BidderWBApi["bidder/wb_api.py"]
BaseAPI --> HTTPRequest
BaseAPI --> Exceptions
BaseAPI --> Protocols
AdvMixin --> BaseAPI
ContentMixin --> BaseAPI
StatisticMixin --> BaseAPI
AdvRightsChecker --> CheckRighter
CheckRighter --> Exceptions
CheckRighter --> HTTPRequest
AdvData --> Protocols
AdvStatClasses --> Protocols
ClientBotWBApi --> BaseAPI
ClientBotWBApi --> AdvMixin
ClientBotWBApi --> ContentMixin
ShopRunnerWBApi --> BaseAPI
ShopRunnerWBApi --> AdvMixin
ShopRunnerWBApi --> ContentMixin
ShopRunnerWBApi --> StatisticMixin
BidderWBApi --> BaseAPI
BidderWBApi --> AdvMixin
style BaseAPI fill:#f9f,stroke:#333
style HTTPRequest fill:#9f9,stroke:#333
style Exceptions fill:#f96,stroke:#333
```

**Diagram sources**
- [base.py](file://app/core/wb_api/base.py)
- [http_request.py](file://app/core/wb_api/http_request.py)
- [adv_rights_checker.py](file://app/core/wb_api/mixins/adv_rights_checker.py)

**Section sources**
- [base.py](file://app/core/wb_api/base.py)
- [http_request.py](file://app/core/wb_api/http_request.py)
- [check_righter.py](file://app/core/wb_api/check_righter.py)

## Performance Considerations
When making bulk requests to the Wildberries API, performance can be optimized by using the chunks utility method to divide large requests into smaller batches that comply with API rate limits. The adaptive retry mechanism automatically adjusts pause times between requests based on success or failure, helping to avoid rate limiting while maximizing throughput. For frequently accessed data, caching responses in Redis can significantly reduce API call volume and improve response times. The system's token rotation mechanism also contributes to performance by ensuring that API calls continue to succeed even when individual tokens have permission issues.

**Section sources**
- [base.py](file://app/core/wb_api/base.py#L65-L70)
- [http_request.py](file://app/core/wb_api/http_request.py#L0-L213)
- [redis_manager.py](file://app/modules/shop_runner/shop_run_worker/redis_manager/redis_manager.py)

## Troubleshooting Guide
Common issues with the Wildberries API integration include token expiration, rate limiting, and permission errors. Token expiration can be detected through the is_expired property of the WBToken model and should trigger notification to the user to update their token. Rate limiting is handled automatically by the retry mechanism, but persistent issues may require adjusting the rate limits in the try_except_decorator configuration. Permission errors occur when a token lacks the necessary rights for a specific API endpoint and are handled by the set_next_token method, which rotates to a different token. If all tokens lack the necessary permissions, the cabinet is deactivated to prevent further failed attempts.

**Section sources**
- [base.py](file://app/core/wb_api/base.py#L72-L101)
- [models.py](file://app/modules/common_slaves/wildberries/models/models.py#L0-L719)
- [check_righter.py](file://app/core/wb_api/check_righter.py#L0-L59)

## Conclusion
The Wildberries API integration provides a robust foundation for managing advertising campaigns on the Wildberries marketplace. The modular architecture with reusable components enables efficient development across multiple modules while maintaining consistency in API interactions. The comprehensive error handling, token management, and retry logic ensure reliable operation even in the face of API limitations and transient failures. By following the patterns documented here, developers can effectively utilize the API integration layer to build powerful advertising management features. Future improvements should focus on eliminating the duplication between BaseAPI and ABC_WB_API to simplify maintenance and reduce technical debt.