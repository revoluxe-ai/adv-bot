# Design Patterns

<cite>
**Referenced Files in This Document**   
- [app_container.py](file://app/core/di/app_container.py)
- [di_manager.py](file://app/core/di/di_manager.py)
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py)
- [models.py](file://app/modules/wb_adv_updater/models.py)
- [adv_manager.py](file://app/modules/shop_runner/service_manager/modules/adv_manager/adv_manager.py)
- [main_manager.py](file://app/modules/adv_creator/backend/main_manager.py)
- [bidder_func.py](file://app/modules/shop_runner/bidder/bidder_func.py)
- [base_adv.py](file://app/core/wb_api/data_classes/advs/base_adv.py)
- [auction_adv.py](file://app/core/wb_api/data_classes/advs/auction_adv.py)
- [adv_fabric.py](file://app/core/wb_api/data_classes/advs/adv_fabric.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Dependency Injection Pattern](#dependency-injection-pattern)
3. [Repository Pattern](#repository-pattern)
4. [Factory Pattern](#factory-pattern)
5. [Strategy Pattern](#strategy-pattern)
6. [Pattern Usage Guidance](#pattern-usage-guidance)
7. [Conclusion](#conclusion)

## Introduction
The adv-bot system implements several key design patterns to ensure maintainability, testability, and extensibility. This document details the implementation of Dependency Injection, Repository, Factory, and Strategy patterns within the system. Each pattern addresses specific architectural concerns and enables clean separation of concerns, making the codebase more modular and easier to extend. The patterns work together to create a robust foundation for the advertising automation system.

## Dependency Injection Pattern

The Dependency Injection (DI) pattern is implemented in the adv-bot system through the AppContainer and DIManager classes, providing a centralized mechanism for managing dependencies and promoting loose coupling between components. This implementation follows the Inversion of Control principle, where objects receive their dependencies rather than creating them directly.

The AppContainer serves as the main DI container, defining and configuring all application services and their dependencies. It uses the dependency_injector library to manage the lifecycle of services and ensure proper initialization order. The DIManager acts as a context manager that handles the bootstrap process, wiring of dependencies, and proper shutdown of resources.

This pattern enables several key benefits in the adv-bot system:
- **Testability**: Dependencies can be easily mocked or replaced during testing
- **Configuration management**: Application settings are centralized and injected where needed
- **Resource management**: Database connections and other resources are properly initialized and cleaned up
- **Modularity**: Components are loosely coupled, making the system more maintainable

```mermaid
classDiagram
class AppContainer {
+settings : Singleton
+redis_client : Singleton
+redis_client_wrapper : Singleton
+module_resources : Container
+_redis_lifecycle : Resource
+wiring_config : WiringConfiguration
}
class DIManager {
-_container : T
-_wired : bool
+create(container_cls) DIManager[T]
+_bootstrap() None
+_wire_module_containers() None
+__aenter__() T
+__aexit__(exc_type, exc_val, exc_tb) None
}
class RedisClient {
+redis_client : Redis
+get(key) Any
+set(key, value) None
+delete(key) None
}
AppContainer --> RedisClient : "uses"
DIManager --> AppContainer : "manages"
DIManager --> RedisClient : "provides"
```

**Diagram sources**
- [app_container.py](file://app/core/di/app_container.py#L1-L96)
- [di_manager.py](file://app/core/di/di_manager.py#L1-L96)

**Section sources**
- [app_container.py](file://app/core/di/app_container.py#L1-L96)
- [di_manager.py](file://app/core/di/di_manager.py#L1-L96)

## Repository Pattern

The Repository Pattern is implemented across the data access layers of the adv-bot system, providing an abstraction between the domain logic and data storage mechanisms. This pattern is particularly evident in the handling of WBToken and WBCabinet models, where repository-like functionality is encapsulated in data manager classes.

The implementation separates data access logic from business logic, allowing the system to interact with data sources through a collection-like interface. This abstraction enables easier testing, as repositories can be mocked or replaced with in-memory implementations during unit tests. It also provides a single point of control for data access operations, making it easier to implement caching, logging, and error handling.

Key components of the Repository Pattern implementation include:
- Data manager classes that encapsulate data access logic
- Use of SQLAlchemy for database operations with proper session management
- Integration with Redis for caching frequently accessed data
- Type-safe data transfer objects for domain entities

The pattern enables the system to work with different data sources transparently, as the business logic only interacts with the repository interface rather than the underlying data storage mechanism.

```mermaid
classDiagram
class DataManager {
+get_keywords_statistic_clickhouse(adv_setting, pass_time, last_views) list[CalculatedKeyword]
+get_good_bad_phrases(adv) list[CalculatedKeyword]
+get_full_adv_stat_for_adv_id_from_redis(adv_id) FullAdvStat | None
+get_wb_category(adv_setting) WBCategory | None
+get_main_photos(nmids) list[str]
}
class AdvSetting {
+adv_id : int
+search_adv_id : int | None
+max_place : int
+max_cpm : int
+reset_place : bool
+name : str
+bidder_active : bool
+wb_cabinet : WBCabinet
+parsing_active : bool
+bot_active : bool
+auto_adv_target_status : bool
+auto_update_white_list : bool
+auto_update_target_place : bool
+active_status : str
+type : int
+nmids : list[int]
+hard_min_ctr : float
}
class WBCabinet {
+id : int
+name : str
+wb_user_cabinet : WBUserCabinet
}
class GlobalCategorySetting {
+id : int
+category_name : str
+min_ctr : float
}
DataManager --> AdvSetting : "manages"
DataManager --> WBCabinet : "accesses"
DataManager --> GlobalCategorySetting : "accesses"
```

**Diagram sources**
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L799)
- [models.py](file://app/modules/wb_adv_updater/models.py#L1-L52)

**Section sources**
- [data_manager.py](file://app/modules/wb_adv_updater/data_manager.py#L1-L799)
- [models.py](file://app/modules/wb_adv_updater/models.py#L1-L52)

## Factory Pattern

The Factory Pattern is implemented in the adv-bot system through the AdvManager and MainAdvManager classes, which handle the creation of different types of advertising campaigns. This pattern provides a flexible way to create complex objects without exposing the instantiation logic to the client.

The implementation allows for the creation of various ad types, including auto-ads and search-ads, through a unified interface. The factory methods encapsulate the complexity of ad creation, including validation, configuration, and integration with external APIs. This abstraction enables the system to easily extend support for new ad types without modifying existing client code.

Key aspects of the Factory Pattern implementation include:
- Centralized creation logic in the MainAdvManager class
- Support for complex ad creation workflows involving multiple steps
- Integration with external APIs for ad creation and configuration
- Error handling and validation during the creation process

The pattern promotes code reuse and reduces duplication by centralizing the ad creation logic, making it easier to maintain and extend as new requirements emerge.

```mermaid
classDiagram
class AdvManager {
+get_complex_adv(adv, keywords) ComplexAdv
}
class MainAdvManager {
+access : WBCabinetAccess
+wb_api : WBApi
+create_complex_advs(bot, user_telegram_id, nmid, hard_mode) tuple[int, int]
+start_complex_advs(nmid, auto_adv_id, search_adv_id) None
+get_adv_setting_by_nmid(nmid) AdvSetting
+_create_search_adv(nmid, name) int
+_create_auto_adv(name, SubjectID, balance_type, start_status) int
+upcast_auto_adv(nmid, auto_adv_id, user_telegram_id, bot) None
+_check_enough_balance(balances) bool
+_get_balance_type(balances) tuple[int, str]
}
class ComplexAdv {
+adv : AdvSetting
+keywords : list[CalculatedKeyword]
}
class AdvSetting {
+adv_id : int
+search_adv_id : int | None
+max_place : int
+max_cpm : int
+reset_place : bool
+name : str
+bidder_active : bool
+wb_cabinet : WBCabinet
+parsing_active : bool
+bot_active : bool
+auto_adv_target_status : bool
+auto_update_white_list : bool
+auto_update_target_place : bool
+active_status : str
+type : int
+nmids : list[int]
+hard_min_ctr : float
}
class CalculatedKeyword {
+text : str
+clicks : int
+views : int
+spend : int
+position : int | None
+cluster_name : str | None
+preset : int | None
+predict_ctr : float | None
+baes_ctr : float | None
+calculated_clicks : int | None
+calculated_views : int | None
+status : KeywordStatus
+reason : str | None
+hard_status : int
+relevant : bool | None
+added_clicks : int | None
+keyword_setting_original_id : int | None
+adv_id : int | None
+original_predict_ctr : float | None
+enough_views : int | None
+baes_predict_ctr : float | None
+rating_by_predict_ctr : float | None
+query : str | int | None
+position_update : datetime | None
+best_keyword_status : bool | None
+childs_keywords : list[CalculatedKeyword] | None
+cpm : int | None
+promo_position : int | None
+real_position : int | None
+base_position : int | None
+predict_ctr_exponent : float | None
}
AdvManager --> ComplexAdv : "creates"
MainAdvManager --> AdvSetting : "creates"
MainAdvManager --> CalculatedKeyword : "uses"
MainAdvManager --> ComplexAdv : "creates"
```

**Diagram sources**
- [adv_manager.py](file://app/modules/shop_runner/service_manager/modules/adv_manager/adv_manager.py#L1-L11)
- [main_manager.py](file://app/modules/adv_creator/backend/main_manager.py#L1-L326)

**Section sources**
- [adv_manager.py](file://app/modules/shop_runner/service_manager/modules/adv_manager/adv_manager.py#L1-L11)
- [main_manager.py](file://app/modules/adv_creator/backend/main_manager.py#L1-L326)

## Strategy Pattern

The Strategy Pattern is implemented in the adv-bot system through the bidding strategy functionality, allowing different bidding algorithms to be used interchangeably. This pattern is particularly evident in the bidder_func module, which contains the core bidding logic that can be configured based on different strategies.

The implementation enables the system to dynamically select and apply different bidding strategies based on campaign settings and performance metrics. This flexibility allows for optimization of advertising spend and improved campaign performance. The pattern separates the bidding algorithm from the context in which it is used, making it easy to add new strategies without modifying existing code.

Key components of the Strategy Pattern implementation include:
- The run_bidder_process_for_adv function that implements the core bidding logic
- Configuration-driven strategy selection through campaign settings
- Integration with external data sources for decision making
- Extensible design that allows for new strategies to be added

The pattern promotes code maintainability by isolating the bidding logic and making it easier to test and optimize individual strategies independently.

```mermaid
classDiagram
class BidderFunc {
+get_cpms_from_wb(auto_adv, wb_api) set[int] | None
+run_bidder_process_for_adv(adv_setting, wb_api, keywords) None
}
class AdvParameterManager {
+get_min_cpm(adv_setting) int
}
class AdvSetting {
+adv_id : int
+search_adv_id : int | None
+max_place : int
+max_cpm : int
+reset_place : bool
+name : str
+bidder_active : bool
+wb_cabinet : WBCabinet
+parsing_active : bool
+bot_active : bool
+auto_adv_target_status : bool
+auto_update_white_list : bool
+auto_update_target_place : bool
+active_status : str
+type : int
+nmids : list[int]
+hard_min_ctr : float
+bidder_step : int | None
+target_ctr_mode : bool
+target_ctr_mode_strategy : str | None
}
class CalculatedKeyword {
+text : str
+clicks : int
+views : int
+spend : int
+position : int | None
+cluster_name : str | None
+preset : int | None
+predict_ctr : float | None
+baes_ctr : float | None
+calculated_clicks : int | None
+calculated_views : int | None
+status : KeywordStatus
+reason : str | None
+hard_status : int
+relevant : bool | None
+added_clicks : int | None
+keyword_setting_original_id : int | None
+adv_id : int | None
+original_predict_ctr : float | None
+enough_views : int | None
+baes_predict_ctr : float | None
+rating_by_predict_ctr : float | None
+query : str | int | None
+position_update : datetime | None
+best_keyword_status : bool | None
+childs_keywords : list[CalculatedKeyword] | None
+cpm : int | None
+promo_position : int | None
+real_position : int | None
+base_position : int | None
+predict_ctr_exponent : float | None
}
class WBApi {
+update_cpm(adv_id, nmid, cpm) None
+get_advs(adv_ids) list[Adv]
}
BidderFunc --> AdvSetting : "uses"
BidderFunc --> CalculatedKeyword : "uses"
BidderFunc --> WBApi : "uses"
BidderFunc --> AdvParameterManager : "uses"
```

**Diagram sources**
- [bidder_func.py](file://app/modules/shop_runner/bidder/bidder_func.py#L1-L162)

**Section sources**
- [bidder_func.py](file://app/modules/shop_runner/bidder/bidder_func.py#L1-L162)

## Pattern Usage Guidance

When extending the adv-bot codebase, consider the following guidance for using each design pattern:

**Dependency Injection Pattern**: Use this pattern when adding new services or components that have dependencies on other services. Always define dependencies in the AppContainer and inject them through constructor parameters rather than creating them directly. This ensures proper lifecycle management and makes components easier to test.

**Repository Pattern**: Implement this pattern when adding new data access functionality. Create data manager classes that encapsulate data access logic and provide a clean interface to the rest of the system. Use the existing DataManager as a reference for proper session management and error handling.

**Factory Pattern**: Apply this pattern when creating complex objects with multiple configuration options or when the creation process involves multiple steps. Centralize creation logic in factory classes and provide clear interfaces for creating different variants of objects.

**Strategy Pattern**: Use this pattern when implementing algorithms that may have multiple variations or when the algorithm needs to be selected at runtime based on configuration or conditions. Define clear interfaces for strategies and ensure they can be easily swapped without affecting the rest of the system.

These patterns work together to create a maintainable and extensible codebase. When adding new features, consider how these patterns can be leveraged to ensure consistency with the existing architecture.

## Conclusion

The adv-bot system effectively implements several key design patterns to create a maintainable, testable, and extensible codebase. The Dependency Injection pattern provides a robust mechanism for managing dependencies and promoting loose coupling. The Repository Pattern abstracts data access logic, making it easier to work with different data sources and improving testability. The Factory Pattern centralizes object creation logic, reducing duplication and making it easier to extend support for new ad types. Finally, the Strategy Pattern enables flexible bidding algorithms that can be configured and optimized based on campaign requirements.

These patterns work together to create a solid architectural foundation that supports the complex requirements of advertising automation. By following the established patterns when extending the codebase, developers can ensure consistency and maintainability across the system.