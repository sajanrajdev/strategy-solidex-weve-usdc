from brownie import (
    accounts,
    interface,
    Controller,
    SettV4,
    StrategySolidexRenBTCwBTCHelper,
)
from config import (
    BADGER_DEV_MULTISIG,
    FEES
)
from dotmap import DotMap
import pytest
from rich.console import Console

console = Console()


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


def deploy(sett_config):
    """
    Deploys, vault, controller and strats and wires them up for you to test
    """
    deployer = accounts[0]

    strategist = deployer
    keeper = deployer
    guardian = deployer

    governance = accounts.at(BADGER_DEV_MULTISIG, force=True)

    controller = Controller.deploy({"from": deployer})
    controller.initialize(BADGER_DEV_MULTISIG, strategist, keeper, BADGER_DEV_MULTISIG)

    # Deploy vault
    sett = SettV4.deploy({"from": deployer})

    args = [
        sett_config.WANT,
        controller,
        BADGER_DEV_MULTISIG,
        keeper,
        guardian,
        False,
        "prefix",
        "PREFIX",
    ]

    # Initialize vault
    sett.initialize(*args)

    sett.unpause({"from": governance})

    # Add vault to controller
    controller.setVault(sett.token(), sett)

    # Deploy strat
    strategy = StrategySolidexRenBTCwBTCHelper.deploy({"from": deployer})

    args = [
        BADGER_DEV_MULTISIG,
        strategist,
        controller,
        keeper,
        guardian,
        sett_config.WANT,
        FEES,
    ]

    # Initialize strat
    strategy.initialize(*args)

    ## Wire up Controller to strat
    controller.approveStrategy(strategy.want(), strategy, {"from": governance})
    controller.setStrategy(strategy.want(), strategy, {"from": deployer})

    # Get whale
    whale = accounts.at(sett_config.WHALE, force=True)

    ## Set up tokens
    want = interface.IERC20(strategy.want())

    # Transfer want from whale
    want.transfer(deployer.address, want.balanceOf(whale.address)/3, {"from": whale})

    assert want.balanceOf(deployer.address) > 0

    return DotMap(
        governance=governance,
        deployer=deployer,
        controller=controller,
        sett=sett,
        strategy=strategy,
        want=want,
    )
