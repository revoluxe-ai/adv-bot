import typing



if typing.TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.new_bids_calculator.update_bids_command import \
    UpdateBidsCommand
    from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager.redis_command import \
    RedisCommand

def update_bids_command_to_redis_command(update_bids_command: "UpdateBidsCommand") -> list[RedisCommand]:
    redis_commands: list[RedisCommand] = []
    for bid in update_bids_command.new_bids:
        redis_command = RedisCommand(adv_id=bid.adv_id,
                                     text=bid.cluster,
                                     bidder_keyword_status=bid.bidder_keyword_status)
        redis_commands.append(redis_command)
    return redis_commands



def dto_to_redis_commands(adv: "ComplexAdv", texts: list[str]) -> list[RedisCommand]:
    redis_commands: list[RedisCommand] = []
    for text in texts:
        redis_command = RedisCommand(
            adv_id=adv.adv_id,
            text=text,
            bidder_keyword_status=None,
        )
        redis_commands.append(redis_command)
    return redis_commands
