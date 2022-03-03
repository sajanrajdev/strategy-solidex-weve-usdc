import time

from brownie import (
    accounts,
    network,
    StrategyGenericSolidexHelper,
    SettV4,
    AdminUpgradeabilityProxy,
    Controller,
    BadgerRegistry,
)

from config import WANT, FEES, REGISTRY

from helpers.constants import AddressZero

import click
from rich.console import Console

console = Console()

sleep_between_tx = 1


def main():
    """
    FOR STRATEGISTS AND GOVERNANCE
    Deploys a Controller, a SettV4 and your strategy under upgradable proxies and wires them up.
    Note that it sets your deployer account as the governance for the three contracts so that
    the setup and production tests are simpler and more efficient. The rest of the permissioned actors
    are set based on the latest entries from the Badger Registry.
    """

    # Get deployer account from local keystore
    dev = connect_account()

    # Get actors from registry
    registry = BadgerRegistry.at(REGISTRY)

    strategist = registry.get("governance")
    guardian = registry.get("guardian")
    keeper = registry.get("keeper")
    proxyAdmin = registry.get("proxyAdminTimelock")

    assert strategist != AddressZero
    assert guardian != AddressZero
    assert keeper != AddressZero
    assert proxyAdmin != AddressZero

    # Deploy controller
    controller = Controller.at("0x72ac086a5d7e1221a6d47438c45ed199e9bff423")

    # Deploy Vault
    vault = SettV4.at("0xb6d63a4e5ca740e96c26adabcac73be78ee39dc5")

    # Deploy Strategy
    strategy = deploy_strategy(
        controller.address,
        dev.address,  # Deployer will be set as governance for testing stage
        strategist,
        keeper,
        guardian,
        dev,
        proxyAdmin,
    )

    # Wire up vault and strategy to test controller
    wire_up_test_controller(controller, vault, strategy, dev)


def deploy_controller(dev, proxyAdmin):

    controller_logic = Controller.at(
        "0xc09ECb36De87AAe031ba0E824a5DF94Ab799754f"
    )  # Controller Logic on FTM

    # Deployer address will be used for all actors as controller will only be used for testing
    args = [
        dev.address,
        dev.address,
        dev.address,
        dev.address,
    ]

    controller_proxy = AdminUpgradeabilityProxy.deploy(
        controller_logic,
        proxyAdmin,
        controller_logic.initialize.encode_input(*args),
        {"from": dev},
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(controller_proxy)
    controller_proxy = Controller.at(controller_proxy.address)

    console.print(
        "[green]Controller was deployed at: [/green]", controller_proxy.address
    )

    return controller_proxy


def deploy_vault(controller, governance, keeper, guardian, dev, proxyAdmin):

    args = [
        WANT,
        controller,
        governance,
        keeper,
        guardian,
        False,
        "",
        "",
    ]

    print("Vault Arguments: ", args)

    vault_logic = SettV4.at(
        "0x18E31A50cEe0b8c716870c1bc8Bc7796e9CcD9ed"
    )  # SettV4h on FTM Logic

    vault_proxy = AdminUpgradeabilityProxy.deploy(
        vault_logic,
        proxyAdmin,
        vault_logic.initialize.encode_input(*args),
        {"from": dev},
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(vault_proxy)
    vault_proxy = SettV4.at(vault_proxy.address)

    console.print("[green]Vault was deployed at: [/green]", vault_proxy.address)

    assert vault_proxy.paused()

    vault_proxy.unpause({"from": dev})

    assert vault_proxy.paused() == False

    return vault_proxy


def deploy_strategy(
    controller, governance, strategist, keeper, guardian, dev, proxyAdmin
):

    args = [
        governance,
        strategist,
        controller,
        keeper,
        guardian,
        WANT,
        FEES,
    ]

    print("Strategy Arguments: ", args)

    strat_logic = StrategyGenericSolidexHelper.at("0x2b7f219d0f574d1bb7893bdddb67e40f4aa8d10d")

    strat_proxy = AdminUpgradeabilityProxy.deploy(
        strat_logic,
        proxyAdmin,
        strat_logic.initialize.encode_input(*args),
        {"from": dev, "allow_revert": True, "gas_limit": 800000},
    )
    time.sleep(sleep_between_tx)

    ## We delete from deploy and then fetch again so we can interact
    AdminUpgradeabilityProxy.remove(strat_proxy)
    strat_proxy = StrategyGenericSolidexHelper.at(strat_proxy.address)

    console.print("[green]Strategy was deployed at: [/green]", strat_proxy.address)

    return strat_proxy


def wire_up_test_controller(controller, vault, strategy, dev):
    controller.approveStrategy(WANT, strategy.address, {"from": dev})
    time.sleep(sleep_between_tx)
    assert controller.approvedStrategies(WANT, strategy.address) == True

    controller.setStrategy(WANT, strategy.address, {"from": dev})
    time.sleep(sleep_between_tx)
    assert controller.strategies(WANT) == strategy.address

    controller.setVault(WANT, vault.address, {"from": dev})
    time.sleep(sleep_between_tx)
    assert controller.vaults(WANT) == vault.address

    console.print("[blue]Controller wired up![/blue]")


def connect_account():
    click.echo(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    click.echo(f"You are using: 'dev' [{dev.address}]")
    return dev
