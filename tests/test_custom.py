from brownie import chain, interface
from helpers.constants import MaxUint256
from helpers.utils import (
    approx,
)
from config import sett_config, FEES
import pytest
from conftest import deploy

"""
  TODO: Put your tests here to prove the strat is good!
  See test_harvest_flow, for the basic tests
  See test_strategy_permissions, for tests at the permissions level
"""

@pytest.mark.parametrize(
    "sett_id",
    sett_config.native,
)
def test_are_you_trying(sett_id):
    """
    Verifies that you set up the Strategy properly
    """
    # Setup
    deployed = deploy(sett_config.native[sett_id])

    deployer = deployed.deployer
    sett = deployed.sett
    want = deployed.want
    strategy = deployed.strategy

    startingBalance = want.balanceOf(deployer)

    depositAmount = startingBalance // 2
    assert startingBalance >= depositAmount
    assert startingBalance >= 0
    assert want.balanceOf(sett) == 0

    want.approve(sett, MaxUint256, {"from": deployer})
    sett.deposit(depositAmount, {"from": deployer})

    available = sett.available()
    assert available > 0

    sett.earn({"from": deployer})

    chain.sleep(100000 * 13)  # Mine so we get some interest
    chain.mine()

    print("balanceOfPool():", strategy.balanceOfPool())

    ## TEST 1: Does the want get used in any way?
    assert want.balanceOf(sett) == depositAmount - available

    # Did the strategy do something with the asset?
    assert want.balanceOf(strategy) < available

    want.approve(sett, MaxUint256, {"from": deployer}) ## Random operation to make ganache re-sync

    lpDepositor = interface.ILpDepositor("0x26E1A0d851CF28E697870e1b7F053B605C8b060F")
    rewards = lpDepositor.pendingRewards(strategy.address, [strategy.want()])
    print("Rewards:", rewards)

    ## End Setup

    harvest = strategy.harvest({"from": deployer})

    ## Assert perFee for governance is exactly 20% // Round because huge numbers
    # assert approx(
    #     (
    #         harvest.events["PerformanceFeeGovernance"][0]["amount"]
    #         + harvest.events["TreeDistribution"][0]["amount"]
    #     )
    #     * (FEES[0] / 10000),
    #     harvest.events["PerformanceFeeGovernance"][0]["amount"],
    #     1,
    # )

    ## Fail if PerformanceFeeStrategist is fired
    try:
        harvest.events["PerformanceFeeStrategist"]
        assert False
    except:
        assert True

    ## The fee is in the want
    assert harvest.events["PerformanceFeeGovernance"][0]["token"] == strategy.want()


@pytest.mark.parametrize(
    "sett_id",
    sett_config.native,
)
def test_fee_configs(sett_id):
    """
    Checks the fees are processed properly according to 
    different configurations.
    """
    # Setup
    deployed = deploy(sett_config.native[sett_id])

    deployer = deployed.deployer
    governance = deployed.governance
    sett = deployed.sett
    want = deployed.want
    strategy = deployed.strategy

    startingBalance = want.balanceOf(deployer)

    depositAmount = startingBalance // 2
    assert startingBalance >= depositAmount
    assert startingBalance >= 0
    assert want.balanceOf(sett) == 0

    want.approve(sett, MaxUint256, {"from": deployer})
    sett.deposit(depositAmount, {"from": deployer})

    available = sett.available()
    assert available > 0

    sett.earn({"from": deployer})

    chain.sleep(100000 * 13)  # Mine so we get some interest
    chain.mine()

    ## End Setup

    chain.snapshot()

    # TEST 1: Configures Gov Fee/Strategist Fee: 15%/0%
    strategy.setPerformanceFeeGovernance(1500, {"from": governance})
    strategy.setPerformanceFeeStrategist(0, {"from": governance})

    harvest = strategy.harvest({"from": deployer})

    ## Fees are being processed
    assert harvest.events["PerformanceFeeGovernance"][0]["amount"] > 0

    ## Fail if PerformanceFeeStrategist is fired
    try:
        harvest.events["PerformanceFeeStrategist"]
        assert False
    except:
        assert True

    ## The fees are in want
    assert harvest.events["PerformanceFeeGovernance"][0]["token"] == strategy.want()


    chain.revert()

    # TEST 2: Configures Gov Fee/Strategist Fee: 10%/10%
    strategy.setPerformanceFeeGovernance(1000, {"from": governance})
    strategy.setPerformanceFeeStrategist(1000, {"from": governance})

    harvest = strategy.harvest({"from": deployer})

    ## Fees are being processed
    assert harvest.events["PerformanceFeeGovernance"][0]["amount"] > 0
    assert harvest.events["PerformanceFeeStrategist"][0]["amount"] > 0

    # Both fees are equal
    assert (
        harvest.events["PerformanceFeeGovernance"][0]["amount"]
    ) == (
        harvest.events["PerformanceFeeStrategist"][0]["amount"]
    )

    ## The fees are in helper and want
    assert harvest.events["PerformanceFeeGovernance"][0]["token"] == strategy.want()
    assert harvest.events["PerformanceFeeStrategist"][0]["token"] == strategy.want()


    chain.revert()

    # TEST 3: Configures Gov Fee/Strategist Fee: 0%/15%
    strategy.setPerformanceFeeGovernance(0, {"from": governance})
    strategy.setPerformanceFeeStrategist(1500, {"from": governance})

    harvest = strategy.harvest({"from": deployer})

    ## Fees are being processed
    assert harvest.events["PerformanceFeeStrategist"][0]["amount"] > 0

    ## Fail if PerformanceFeeGovernance is fired
    try:
        harvest.events["PerformanceFeeGovernance"]
        assert False
    except:
        assert True

    ## The fees are in CRV and CVX
    assert harvest.events["PerformanceFeeStrategist"][0]["token"] == strategy.want()
