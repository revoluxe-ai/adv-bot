from typing import TYPE_CHECKING, cast
from app.core.redis_manager_v2.base_redis_manager import BaseRedisManager
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager import \
    convertor
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import \
        UpdateBidsCommand
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_command import RedisCommand


class RedisKeywordBidderStatusManager(BaseRedisManager):
    prefix: str = 'bidder-keyword-status'
    default_ttl: int | None = 60 * 60 * 12

    def _get_effective_ttl(self) -> int | None:
        # Если TTL переопределили на экземпляре (как в тестах), используем его.
        if "default_ttl" in self.__dict__:
            return self.default_ttl
        return self._resolve_ttl()

    def _get_key(self, redis_command: RedisCommand) -> str:
        adv_id = redis_command.adv_id
        nmid = redis_command.nmid
        text = redis_command.text
        return f'{self.prefix}-{adv_id}-{nmid}-{text}'


    async def update_statuses(self, update_bids_command: "UpdateBidsCommand") -> None:
        redis_commands: list[RedisCommand] = convertor.update_bids_command_to_redis_command(update_bids_command)
        await self._update_statuses(redis_commands)



    async def _update_statuses(self, redis_commands: list[RedisCommand]) -> None:
        ttl = self._get_effective_ttl()
        async with self._client.write_pipeline() as pipeline:  # type: ignore[reportUnknownMemberType]
            for redis_command in redis_commands:
                bidder_keyword_status: BidderKeywordStatus | None = redis_command.bidder_keyword_status
                if bidder_keyword_status is not None:
                    key: str = self._get_key(redis_command)
                    if ttl is not None:
                        pipeline.set(key, bidder_keyword_status, ex=ttl)
                    else:
                        pipeline.set(key, bidder_keyword_status)
            await pipeline.execute()  # type: ignore[reportUnknownMemberType]


    async def get_statuses(self,
                           adv: ComplexAdv,
                           texts: list[str]) -> dict[str, BidderKeywordStatus]:
        normalized_texts =  texts
        redis_commands: list[RedisCommand] = convertor.dto_to_redis_commands(adv, normalized_texts)
        statuses = await self._get_statuses(redis_commands)
        rows = zip(normalized_texts, statuses)
        text_to_status: dict[str, BidderKeywordStatus] = dict()
        for text, status in rows:
            status: BidderKeywordStatus = status
            text_to_status[text] = status
        return text_to_status

    async def _get_statuses(self, redis_commands: list[RedisCommand]) -> list[BidderKeywordStatus]:
        async with self._client.read_pipeline() as pipeline:  # type: ignore[reportUnknownMemberType]
            for redis_command in redis_commands:
                key = self._get_key(redis_command)
                pipeline.get(key)
            results = cast(list[str | None], await pipeline.execute())  # type: ignore[reportUnknownMemberType]
        statuses: list[BidderKeywordStatus] = []
        for result in results:
            if result is not None:
                try:
                    status = BidderKeywordStatus(result)
                except ValueError:
                    status = BidderKeywordStatus.GOOD
            else:
                status = BidderKeywordStatus.GOOD
            statuses.append(status)
        return statuses






