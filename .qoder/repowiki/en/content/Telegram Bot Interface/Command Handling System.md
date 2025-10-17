# Command Handling System

<cite>
**Referenced Files in This Document**   
- [global_router.py](file://app/client_bot/global_router.py)
- [common_routers.py](file://app/client_bot/common_routers.py)
- [start.py](file://app/client_bot/user_interface/handlers/start/start.py)
- [change_cpm.py](file://app/client_bot/user_interface/handlers/change_cpm.py)
- [adv_setting.py](file://app/client_bot/user_interface/handlers/adv_setting.py)
- [states.py](file://app/client_bot/user_interface/states.py)
- [callbacks.py](file://app/client_bot/user_interface/views/callbacks.py)
- [templates.py](file://app/client_bot/user_interface/message_templates/templates.py)
- [keyboards.py](file://app/client_bot/user_interface/views/keyboards.py)
- [bot.py](file://app/client_bot/bot.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Router Architecture](#router-architecture)
3. [Command Handler Structure](#command-handler-structure)
4. [Key Command Handlers](#key-command-handlers)
5. [State Management and FSM](#state-management-and-fsm)
6. [Dependency Injection and External Integrations](#dependency-injection-and-external-integrations)
7. [Error Handling Patterns](#error-handling-patterns)
8. [Best Practices for Command Development](#best-practices-for-command-development)
9. [Performance Considerations](#performance-considerations)
10. [Conclusion](#conclusion)

## Introduction
The Telegram bot's command handling system is built on the aiogram framework, utilizing a hierarchical router architecture to organize command handlers by functionality and user roles. The system implements a sophisticated state management approach using Finite State Machine (FSM) patterns to handle multi-step interactions. Command handlers are organized across multiple router modules, with dependency injection providing access to business logic and external APIs. The architecture supports complex workflows for onboarding, campaign configuration, and bid management while maintaining separation of concerns and testability.

**Section sources**
- [global_router.py](file://app/client_bot/global_router.py#L1-L30)
- [common_routers.py](file://app/client_bot/common_routers.py#L1-L104)

## Router Architecture

```mermaid
graph TD
GlobalRouter[Global Router] --> CommonRouter[Common Router]
GlobalRouter --> StartRouter[Start Router]
GlobalRouter --> BonusRouter[Bonus Scene Router]
GlobalRouter --> AddBalanceRouter[Add Balance Router]
GlobalRouter --> RefProgramRouter[Referral Program Router]
CommonRouter --> KeywordsPositionsRouter[Keywords Positions History]
CommonRouter --> ManualUpdateRouter[Manual Phrase Positions Update]
CommonRouter --> AutoUpdaterRouter[Auto Updater Target Place]
CommonRouter --> WhiteListUpdaterRouter[Auto White List Updater]
CommonRouter --> KeywordRelevantRouter[Keyword Relevant Setting]
CommonRouter --> OrdersSourceRouter[Orders Source Toggle]
CommonRouter --> BidderAutoModeRouter[Bidder Auto Mode]
CommonRouter --> SalesPlanRouter[Sales Plan Settings]
CommonRouter --> AuctionBoostRouter[Auction Boost Mode Settings]
CommonRouter --> ExponentSettingRouter[Exponent Setting in Adv Setting]
CommonRouter --> BidderStepSettingRouter[Bidder Step Setting]
CommonRouter --> AdvCreatorRouter[Adv Creator]
CommonRouter --> ResetPlaceRouter[Reset Place Setting]
CommonRouter --> BidderRouter[Bidder]
CommonRouter --> ChangeCPMRouter[Change CPM]
CommonRouter --> FavoriteAdvsRouter[Favorite Advs for Users]
CommonRouter --> ClustersRouter[Clusters]
CommonRouter --> DownloadKeywordsRouter[Download Keywords]
CommonRouter --> AdvSettingRouter[Adv Setting]
CommonRouter --> AddBlackPhrasesRouter[Add Black Phrases]
CommonRouter --> CPMBuilderRouter[CPM Builder]
CommonRouter --> GetShopForAdminRouter[Get Shop for Admin]
CommonRouter --> KeywordSettingsRouter[Keyword Settings]
CommonRouter --> AddWhitePhrasesRouter[Add White Phrases]
CommonRouter --> SettingMinCTRRouter[Setting Min CTR]
CommonRouter --> ChangeMaxCPCRouter[Change Max CPC]
CommonRouter --> MinViewsRouter[Min Views for ML Predict CTR]
CommonRouter --> UpdateAdvRouter[Update Adv]
CommonRouter --> StrategySettingRouter[Strategy Setting]
CommonRouter --> ShopSettingsRouter[Shop Settings]
```

**Diagram sources**
- [global_router.py](file://app/client_bot/global_router.py#L1-L30)
- [common_routers.py](file://app/client_bot/common_routers.py#L1-L104)

**Section sources**
- [global_router.py](file://app/client_bot/global_router.py#L1-L30)
- [common_routers.py](file://app/client_bot/common_routers.py#L1-L104)

## Command Handler Structure

The command handling system follows a modular architecture with handlers organized by functionality. The global_router.py serves as the entry point, importing and including routers from various modules. The common_routers.py file aggregates most command handlers, importing routers from both core functionality modules and specific handler files in the user_interface directory.

The system uses a hierarchical inclusion pattern where the global router includes the common router, which in turn includes individual feature routers. This structure allows for centralized middleware application and ensures proper execution order, particularly important for the /start command which must be processed before other handlers.

Command handlers are implemented as callback query and message handlers, with callback data classes defined in callbacks.py providing type-safe payload structures. Message templates in templates.py handle response formatting, while keyboards.py manages interactive button layouts.

**Section sources**
- [global_router.py](file://app/client_bot/global_router.py#L1-L30)
- [common_routers.py](file://app/client_bot/common_routers.py#L1-L104)
- [templates.py](file://app/client_bot/user_interface/message_templates/templates.py#L1-L186)
- [keyboards.py](file://app/client_bot/user_interface/views/keyboards.py#L1-L1161)

## Key Command Handlers

### Onboarding Handler (start.py)

```mermaid
flowchart TD
Start[/start command] --> StateClear["Clear FSM state"]
StateClear --> UserCheck["Check if user exists in DB"]
UserCheck --> CabinetCheck{"Has cabinets?"}
CabinetCheck --> |Yes| ShowCabinets["Display cabinet selection"]
CabinetCheck --> |No| CabinetName["Request cabinet name"]
CabinetName --> TokenInput["Request API token"]
TokenInput --> TokenValidation["Validate token with WB API"]
TokenValidation --> OwnershipCheck{"Token already used?"}
OwnershipCheck --> |Yes| Error["Show error message"]
OwnershipCheck --> |No| ShopIdCheck["Extract shop ID from token"]
ShopIdCheck --> CabinetExists{"Cabinet exists?"}
CabinetExists --> |Yes| LinkToExisting["Link to existing cabinet"]
CabinetExists --> |No| CreateNew["Create new cabinet"]
CreateNew --> UpdateData["Update shop data from WB"]
UpdateData --> ShowCabinets
```

**Diagram sources**
- [start.py](file://app/client_bot/user_interface/handlers/start/start.py#L1-L445)

**Section sources**
- [start.py](file://app/client_bot/user_interface/handlers/start/start.py#L1-L445)
- [states.py](file://app/client_bot/user_interface/states.py#L1-L79)

### Bid Adjustment Handler (change_cpm.py)

```mermaid
sequenceDiagram
participant User
participant Bot
participant State
participant Database
participant WB_API
User->>Bot : Click "Change CPM" button
Bot->>State : Store adv_setting_original_id
Bot->>User : Request new CPM value
User->>Bot : Enter CPM value
Bot->>Bot : Validate input (numeric, ≤3000)
Bot->>Database : Retrieve AdvSetting by ID
Database-->>Bot : Return AdvSetting with shop_id
Bot->>WB_API : Get access for shop_id
WB_API-->>Bot : Return access credentials
Bot->>WB_API : Update CPM for auto and search ads
WB_API-->>Bot : Confirmation
Bot->>User : Confirm CPM update
```

**Diagram sources**
- [change_cpm.py](file://app/client_bot/user_interface/handlers/change_cpm.py#L1-L84)

**Section sources**
- [change_cpm.py](file://app/client_bot/user_interface/handlers/change_cpm.py#L1-L84)
- [callbacks.py](file://app/client_bot/user_interface/views/callbacks.py#L1-L223)

### Campaign Configuration Handler (adv_setting.py)

```mermaid
classDiagram
class AdvSettingHandler {
+reset_filter()
+waiting_for_keywords_for_filter()
+choice_adv_paginator()
+adv_handler()
+turn_adv_on()
+turn_adv_off_all()
+turn_adv_off()
+turn_on_auto_min_ctr()
+turn_off_auto_min_ctr()
}
class BalanceManager {
+get_cabinet_balance_and_bonuses()
}
class Pricer {
+get_price_for_day_for_shop()
+get_tariff_for_day()
}
class WBUserCabinet {
+id : int
+name : str
+user_id : int
+wb_cabinet_id : int
}
class AdvSetting {
+id : int
+name : str
+bot_active : bool
+auto_update_white_list : bool
+auto_update_target_place : bool
+orders_source_for_auto_mode : str
+auction_boost_all_phrase_mode : bool
+hard_min_ctr : bool
+reset_place : bool
+clusters_mode : bool
+new_auto_min_ctr_mode : bool
}
AdvSettingHandler --> BalanceManager : "uses"
AdvSettingHandler --> Pricer : "uses"
AdvSettingHandler --> WBUserCabinet : "reads"
AdvSettingHandler --> AdvSetting : "reads/writes"
```

**Diagram sources**
- [adv_setting.py](file://app/client_bot/user_interface/handlers/adv_setting.py#L1-L328)

**Section sources**
- [adv_setting.py](file://app/client_bot/user_interface/handlers/adv_setting.py#L1-L328)
- [callbacks.py](file://app/client_bot/user_interface/views/callbacks.py#L1-L223)
- [keyboards.py](file://app/client_bot/user_interface/views/keyboards.py#L1-L1161)

## State Management and FSM

```mermaid
stateDiagram-v2
[*] --> GlobalState
GlobalState --> CabinetRegistration
CabinetRegistration --> CabinetRegistration : cabinet_name → api
CabinetRegistration --> AdvSetting : complete
GlobalState --> ChangeMinCTR
ChangeMinCTR --> ChangeMinCTR : waiting_for_new_min_ctr
GlobalState --> AddNewToken
AddNewToken --> AddNewToken : token
GlobalState --> CreateNewAdvCompany
CreateNewAdvCompany --> CreateNewAdvCompany : waiting_for_name → waiting_for_nmids
GlobalState --> RefProgram
RefProgram --> RefProgram : getting_name
GlobalState --> AdvSetting
AdvSetting --> AdvSetting : waiting_for_filter_by_query → waiting_for_filter_keywords
GlobalState --> ChangeMaxCPC
ChangeMaxCPC --> ChangeMaxCPC : waiting_for_new_max_cpc
GlobalState --> ChangeMinViewsForPredictCTR
ChangeMinViewsForPredictCTR --> ChangeMinViewsForPredictCTR : waiting_for_new_min_views
GlobalState --> AddBalance
AddBalance --> AddBalance : awaiting_confirmation → awaiting_amount
GlobalState --> AdvCompanyCatalog
AdvCompanyCatalog --> AdvCompanyCatalog : waiting_for_keywords_for_filter → waiting_for_sort_type
GlobalState --> AddWhitePhrases
AddWhitePhrases --> AddWhitePhrases : waiting_for_white_phrases
GlobalState --> CPMSetting
CPMSetting --> CPMSetting : waiting_for_min_position → waiting_for_max_cpm → waiting_for_manual_cpm → waiting_for_max_position
GlobalState --> AddBlackPhrasesTemplates
AddBlackPhrasesTemplates --> AddBlackPhrasesTemplates : waiting_for_black_phrases
GlobalState --> AddRelevantPhrases
AddRelevantPhrases --> AddRelevantPhrases : waiting_for_relevant_phrases
GlobalState --> ChangeCPM
ChangeCPM --> ChangeCPM : waiting_for_cpm
GlobalState --> ShopMenuState
ShopMenuState --> ShopMenuState : shop_menu
```

**Diagram sources**
- [states.py](file://app/client_bot/user_interface/states.py#L1-L79)

**Section sources**
- [states.py](file://app/client_bot/user_interface/states.py#L1-L79)
- [start.py](file://app/client_bot/user_interface/handlers/start/start.py#L1-L445)
- [change_cpm.py](file://app/client_bot/user_interface/handlers/change_cpm.py#L1-L84)
- [adv_setting.py](file://app/client_bot/user_interface/handlers/adv_setting.py#L1-L328)

## Dependency Injection and External Integrations

```mermaid
graph TD
Handler[Command Handler] --> DI[Dependency Injection Container]
DI --> Database[Database Session]
DI --> Redis[Redis Manager]
DI --> Config[Configuration]
DI --> WB_API[WB API Client]
DI --> BalanceManager[Balance Manager]
DI --> Pricer[Pricer Service]
Database --> SQLAlchemy[SQLAlchemy ORM]
Redis --> RedisClient[Redis Client]
WB_API --> HTTPClient[AioHTTP Client]
BalanceManager --> Database
Pricer --> Config
Handler --> BusinessLogic[Business Logic Modules]
BusinessLogic --> Database
BusinessLogic --> Redis
BusinessLogic --> WB_API
```

**Diagram sources**
- [core/di](file://app/core/di/)
- [modules/balance_manager](file://app/modules/balance_manager/)
- [core/wb_api](file://app/core/wb_api/)
- [utils/db/session_maker.py](file://app/utils/db/session_maker.py)

**Section sources**
- [adv_setting.py](file://app/client_bot/user_interface/handlers/adv_setting.py#L1-L328)
- [change_cpm.py](file://app/client_bot/user_interface/handlers/change_cpm.py#L1-L84)
- [start.py](file://app/client_bot/user_interface/handlers/start/start.py#L1-L445)

## Error Handling Patterns

The command handling system implements comprehensive error handling at multiple levels. Handlers use try-except blocks to catch specific exceptions from external APIs and database operations. The system distinguishes between user-facing errors (such as invalid input) and system errors (such as API failures), providing appropriate responses for each.

Middleware components handle throttling and callback acknowledgment, ensuring users receive immediate feedback when interacting with buttons. The system also implements timeout handling for long-running operations, particularly when communicating with the Wildberries API for shop updates.

Error messages are standardized through message templates, with different templates for different error types. The system logs all errors with full context for debugging purposes while presenting user-friendly messages that guide users toward resolution.

**Section sources**
- [errors_message.py](file://app/client_bot/user_interface/views/errors_message.py#L1-L29)
- [start.py](file://app/client_bot/user_interface/handlers/start/start.py#L1-L445)
- [change_cpm.py](file://app/client_bot/user_interface/handlers/change_cpm.py#L1-L84)
- [adv_setting.py](file://app/client_bot/user_interface/handlers/adv_setting.py#L1-L328)

## Best Practices for Command Development

When adding new commands to the system, developers should follow these best practices:

1. **Router Organization**: Place new command handlers in appropriate modules based on functionality, and register them in common_routers.py unless they require special ordering in global_router.py.

2. **State Management**: Use dedicated state classes in states.py for multi-step commands, following the naming convention {CommandName}State with appropriate state attributes.

3. **Callback Data**: Define new callback data classes in callbacks.py using the CallbackData base class, ensuring type safety and proper serialization.

4. **Dependency Injection**: Access shared services through the dependency injection system rather than creating direct dependencies, maintaining testability.

5. **Error Handling**: Implement comprehensive error handling with user-friendly messages, logging system errors, and providing clear guidance for resolution.

6. **Circular Import Prevention**: Structure imports to avoid circular dependencies by using string annotations for type hints and importing modules at the function level when necessary.

7. **Testability**: Design handlers to be easily testable by separating business logic from Telegram-specific code and using dependency injection for external services.

**Section sources**
- [common_routers.py](file://app/client_bot/common_routers.py#L1-L104)
- [states.py](file://app/client_bot/user_interface/states.py#L1-L79)
- [callbacks.py](file://app/client_bot/user_interface/views/callbacks.py#L1-L223)

## Performance Considerations

```mermaid
flowchart LR
Sync["Synchronous Operations"]
Async["Asynchronous Operations"]
Sync --> DB["Database Queries"]
Sync --> State["FSM State Operations"]
Sync --> Template["Message Template Rendering"]
Async --> API["External API Calls"]
Async --> Redis["Redis Operations"]
Async --> File["File Operations"]
Async --> Long["Long-running Processes"]
style Sync fill:#f9f,stroke:#333
style Async fill:#bbf,stroke:#333
```

**Diagram sources**
- [start.py](file://app/client_bot/user_interface/handlers/start/start.py#L1-L445)
- [change_cpm.py](file://app/client_bot/user_interface/handlers/change_cpm.py#L1-L84)
- [adv_setting.py](file://app/client_bot/user_interface/handlers/adv_setting.py#L1-L328)

**Section sources**
- [start.py](file://app/client_bot/user_interface/handlers/start/start.py#L1-L445)
- [change_cpm.py](file://app/client_bot/user_interface/handlers/change_cpm.py#L1-L84)
- [adv_setting.py](file://app/client_bot/user_interface/handlers/adv_setting.py#L1-L328)

The command handling system leverages asynchronous execution for optimal performance. All handlers are implemented as async functions to prevent blocking the event loop. The system distinguishes between synchronous operations (such as database queries and state management) and asynchronous operations (such as external API calls and Redis operations).

Long-running operations, particularly those involving communication with the Wildberries API, implement timeout mechanisms to prevent indefinite blocking. The system uses asyncio.wait_for() to enforce timeouts, ensuring that users receive timely feedback even when external services are slow.

Database operations are optimized through the use of SQLAlchemy's async capabilities, with careful management of session lifetimes to prevent connection leaks. Redis operations are similarly handled asynchronously, with pipelining used where appropriate to reduce round-trip times.

The system implements caching strategies through Redis to minimize redundant operations, particularly for frequently accessed data such as user cabinets and campaign settings.

## Conclusion
The Telegram bot's command handling system demonstrates a well-structured architecture that effectively organizes command handlers by functionality and user roles. The hierarchical router system, combined with comprehensive state management and dependency injection, enables the implementation of complex multi-step workflows while maintaining code organization and testability. The integration with business logic modules and external APIs is handled through well-defined interfaces, ensuring separation of concerns. The system's error handling patterns provide robust user experiences, while its asynchronous design ensures responsive performance even during long-running operations.