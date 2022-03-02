## Ideally, they have one file with the settings for the strat and deployment
## This file would allow them to configure so they can test, deploy and interact with the strategy
from dotmap import DotMap

BADGER_DEV_MULTISIG = "0x4c56ee3295042f8A5dfC83e770a21c707CB46f5b"

sett_config = DotMap(
    native = DotMap(
        StrategySolidexRenBTCwBTCHelper = DotMap(
            WANT = "0x6058345A4D8B89Ddac7042Be08091F91a404B80b",  ## WeVE/USDC LP
            LP_COMPONENT =  "0x6058345A4D8B89Ddac7042Be08091F91a404B80b",  ## NOT USED
            REWARD_TOKEN = "0x6058345A4D8B89Ddac7042Be08091F91a404B80b",  ## NOT USED
            WHALE = "0xf9ce347a78dd40f8e02f84431286a4f1153a78bd"
        )
    )
)

## Fees in Basis Points
DEFAULT_GOV_PERFORMANCE_FEE = 1500
DEFAULT_PERFORMANCE_FEE = 0
DEFAULT_WITHDRAWAL_FEE = 10

FEES = [DEFAULT_GOV_PERFORMANCE_FEE, DEFAULT_PERFORMANCE_FEE, DEFAULT_WITHDRAWAL_FEE]

BADGER_TREE = "0x89122c767A5F543e663DB536b603123225bc3823"

REGISTRY = "0xFda7eB6f8b7a9e9fCFd348042ae675d1d652454f"  # Multichain BadgerRegistry
