from config import (
    BADGER_DEV_MULTISIG,
    DEFAULT_GOV_PERFORMANCE_FEE,
    DEFAULT_PERFORMANCE_FEE,
    DEFAULT_WITHDRAWAL_FEE,
)
from config import sett_config
import pytest
from conftest import deploy


@pytest.mark.parametrize(
    "sett_id",
    sett_config.native,
)
def test_deploy_settings(sett_id):
    """
    Verifies that you set up the Strategy properly
    """
    config = sett_config.native[sett_id]
    deployed = deploy(config)
    
    strategy = deployed.strategy

    protected_tokens = strategy.getProtectedTokens()

    ## NOTE: Change based on how you set your contract
    assert protected_tokens[0] == strategy.want()
    assert protected_tokens[1] == strategy.sex()
    assert protected_tokens[2] == strategy.solid()
    assert protected_tokens[3] == strategy.weve()
    assert protected_tokens[4] == strategy.usdc()

    assert strategy.governance() == BADGER_DEV_MULTISIG

    assert strategy.performanceFeeGovernance() == DEFAULT_GOV_PERFORMANCE_FEE
    assert strategy.performanceFeeStrategist() == DEFAULT_PERFORMANCE_FEE
    assert strategy.withdrawalFee() == DEFAULT_WITHDRAWAL_FEE
