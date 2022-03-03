// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "../deps/@openzeppelin/contracts-upgradeable/token/ERC20/IERC20Upgradeable.sol";
import "../deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "../deps/@openzeppelin/contracts-upgradeable/math/MathUpgradeable.sol";
import "../deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "../deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "../interfaces/uniswap/IUniswapRouterV2.sol";
import "../interfaces/badger/IController.sol";
import "../interfaces/badger/ISettV4h.sol";
import "../interfaces/solidex/ILpDepositor.sol";
import "../interfaces/solidly/IBaseV1Router01.sol";
import "../interfaces/curve/ICurveRouter.sol";

import {IBaseV1Pair} from "../interfaces/solidly/IBaseV1Pair.sol";
import {route} from "../interfaces/solidly/IBaseV1Router01.sol";
import {BaseStrategy} from "../deps/BaseStrategy.sol";

contract StrategyGenericSolidexHelper is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    // Solidex
    ILpDepositor public constant lpDepositor =
        ILpDepositor(0x26E1A0d851CF28E697870e1b7F053B605C8b060F);

    // Solidly Doesn't revert on failure
    IBaseV1Router01 public constant SOLIDLY_ROUTER = IBaseV1Router01(0xa38cd27185a464914D3046f0AB9d43356B34829D);

    // Spookyswap, reverts on failure
    IUniswapRouterV2 public constant SPOOKY_ROUTER = IUniswapRouterV2(0xF491e7B69E4244ad4002BC14e878a34207E38c29); // Spookyswap

    // Curve / Doesn't revert on failure
    ICurveRouter public constant CURVE_ROUTER = ICurveRouter(0x74E25054e98fd3FCd4bbB13A962B43E49098586f); // Curve quote and swaps

    
    // ===== Token Registry =====

    IERC20Upgradeable public constant SOLID =
        IERC20Upgradeable(0x888EF71766ca594DED1F0FA3AE64eD2941740A20);
    IERC20Upgradeable public constant SEX =
        IERC20Upgradeable(0xD31Fcd1f7Ba190dBc75354046F6024A9b86014d7);
    IERC20Upgradeable public constant wFTM =
        IERC20Upgradeable(0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83);

    IERC20Upgradeable public constant renBTC = IERC20Upgradeable(0xDBf31dF14B66535aF65AaC99C32e9eA844e14501);
    IERC20Upgradeable public constant wBTC = IERC20Upgradeable(0x321162Cd933E2Be498Cd2267a90534A804051b11);

    IERC20Upgradeable public token0; // Set in initialize, next step toward reusability
    IERC20Upgradeable public token1;


    // Constants
    uint256 public constant MAX_BPS = 10000;

    // slippage tolerance 0.5% (divide by MAX_BPS) - Changeable by Governance or Strategist
    uint256 public sl;

    // Used to signal to the Badger Tree that rewards where sent to it
    event TreeDistribution(
        address indexed token,
        uint256 amount,
        uint256 indexed blockNumber,
        uint256 timestamp
    );
    event PerformanceFeeGovernance(
        address indexed destination,
        address indexed token,
        uint256 amount,
        uint256 indexed blockNumber,
        uint256 timestamp
    );
    event PerformanceFeeStrategist(
        address indexed destination,
        address indexed token,
        uint256 amount,
        uint256 indexed blockNumber,
        uint256 timestamp
    );

    function initialize(
        address _governance,
        address _strategist,
        address _controller,
        address _keeper,
        address _guardian,
        address _want,
        uint256[3] memory _feeConfig
    ) public initializer {
        __BaseStrategy_init(
            _governance,
            _strategist,
            _controller,
            _keeper,
            _guardian
        );
        /// @dev Add config here
        want = _want;

        performanceFeeGovernance = _feeConfig[0];
        performanceFeeStrategist = _feeConfig[1];
        withdrawalFee = _feeConfig[2];

        // Set default slippage value
        sl = 50;

        /// @dev do one off approvals here
        IERC20Upgradeable(want).safeApprove(address(lpDepositor), type(uint256).max);

        // Solidex is 2 rewards, these are hardcoded as they are part of all strategies and can't change
        SOLID.safeApprove(address(SOLIDLY_ROUTER), type(uint256).max);
        SOLID.safeApprove(address(SPOOKY_ROUTER), type(uint256).max);
        SOLID.safeApprove(address(CURVE_ROUTER), type(uint256).max);

        SEX.safeApprove(address(SOLIDLY_ROUTER), type(uint256).max);
        SEX.safeApprove(address(SPOOKY_ROUTER), type(uint256).max);
        SEX.safeApprove(address(CURVE_ROUTER), type(uint256).max);

        // want is LP with 2 tokens
        IBaseV1Pair lpToken = IBaseV1Pair(want);
        token0 = IERC20Upgradeable(lpToken.token0());
        token1 = IERC20Upgradeable(lpToken.token1());

        token0.safeApprove(address(SOLIDLY_ROUTER), type(uint256).max);
        token0.safeApprove(address(SPOOKY_ROUTER), type(uint256).max);
        token0.safeApprove(address(CURVE_ROUTER), type(uint256).max);

        token1.safeApprove(address(SOLIDLY_ROUTER), type(uint256).max);
        token1.safeApprove(address(SPOOKY_ROUTER), type(uint256).max);
        token1.safeApprove(address(CURVE_ROUTER), type(uint256).max);


        // Extra approve is for wFTM as we need a liquid token for certain swaps
        wFTM.safeApprove(address(SOLIDLY_ROUTER), type(uint256).max);
        wFTM.safeApprove(address(SPOOKY_ROUTER), type(uint256).max);
        wFTM.safeApprove(address(CURVE_ROUTER), type(uint256).max);
    }

    /// ===== View Functions =====

    // @dev Specify the name of the strategy
    function getName() external pure override returns (string memory) {
        return "StrategyGenericSolidexHelper";
    }

    // @dev Specify the version of the Strategy, for upgrades
    function version() external pure returns (string memory) {
        return "1.0";
    }

    /// @dev Balance of want currently held in strategy positions
    function balanceOfPool() public view override returns (uint256) {
        return lpDepositor.userBalances(
            address(this),
            want
        );
    }

    /// @dev Returns true if this strategy requires tending
    function isTendable() public view override returns (bool) {
        return false;
    }

    // @dev These are the tokens that cannot be moved except by the vault
    function getProtectedTokens()
        public
        view
        override
        returns (address[] memory)
    {
        address[] memory protectedTokens = new address[](6);
        protectedTokens[0] = want; // renBTC/wBTC Solid LP
        protectedTokens[1] = address(SEX); // Reward1
        protectedTokens[2] = address(SOLID); // Reward2
        protectedTokens[3] = address(wFTM); // Native Token
        protectedTokens[4] = address(token0); // wBTC
        protectedTokens[5] = address(token1); // renBTC
        return protectedTokens;
    }

    /// @notice sets slippage tolerance for liquidity provision
    function setSlippageTolerance(uint256 _s) external whenNotPaused {
        _onlyGovernanceOrStrategist();
        sl = _s;
    }

    /// ===== Internal Core Implementations =====

    /// @dev security check to avoid moving tokens that would cause a rugpull, edit based on strat
    function _onlyNotProtectedTokens(address _asset) internal override {
        address[] memory protectedTokens = getProtectedTokens();

        for (uint256 x = 0; x < protectedTokens.length; x++) {
            require(
                address(protectedTokens[x]) != _asset,
                "Asset is protected"
            );
        }
    }

    /// @dev invest the amount of want
    /// @notice When this function is called, the controller has already sent want to this
    /// @notice Just get the current balance and then invest accordingly
    function _deposit(uint256 _amount) internal override {
        lpDepositor.deposit(want, _amount);
    }

    /// @dev utility function to withdraw everything for migration
    function _withdrawAll() internal override {
        lpDepositor.withdraw(want, balanceOfPool());
    }

    /// @dev withdraw the specified amount of want, liquidate from lpComponent to want, paying off any necessary debt for the conversion
    function _withdrawSome(uint256 _amount)
        internal
        override
        returns (uint256)
    {
        lpDepositor.withdraw(want, _amount);
        return _amount;
    }


    /// @dev Harvest from strategy mechanics, realizing increase in underlying position
    function harvest() external whenNotPaused returns (uint256 harvested) {
        _onlyAuthorizedActors();

        uint256 _before = IERC20Upgradeable(want).balanceOf(address(this));

        // 1. Claim rewards
        address[] memory pools = new address[](1);
        pools[0] = want;
        lpDepositor.getReward(pools);

        // 2. Swap all SOLID for wFTM
        uint256 solidBalance = SOLID.balanceOf(address(this));
        if (solidBalance > 0) {
            _doOptimalSwap(address(SOLID), address(wFTM), solidBalance);
        }

        // 3. Swap all SEX for wFTM
        uint256 sexBalance = SEX.balanceOf(address(this));
        if (sexBalance > 0) {
            _doOptimalSwap(address(SEX), address(wFTM), sexBalance);
        }

        // 4. Swap all wFTM for wBTC
        uint256 wFTMBalance = wFTM.balanceOf(address(this));
        if (wFTMBalance > 0) {
            _doOptimalSwap(address(wFTM), address(token0), wFTMBalance);

            // 5. Swap half wBTC for renBTC
            uint256 _half = token0.balanceOf(address(this)).mul(5000).div(MAX_BPS);
            _doOptimalSwap(address(token0), address(token1), _half);

            // 6. Provide liquidity for WeVe/USDC LP Pair
            uint256 token0In = token0.balanceOf(address(this));
            uint256 token1In = token1.balanceOf(address(this));
            SOLIDLY_ROUTER.addLiquidity(
                address(token0),
                address(token1),
                true, // Stable
                token0In,
                token1In,
                token0In.mul(sl).div(MAX_BPS),
                token1In.mul(sl).div(MAX_BPS),
                address(this),
                now
            );
        }

        // 7. Process Fees
        uint256 earned =
            IERC20Upgradeable(want).balanceOf(address(this)).sub(_before);

        if(earned > 0){
            /// Process fees
            _processRewardsFees(earned, want);

            // Emit to Tree the Helper Vault

            uint256 earnedAfterFees =
                IERC20Upgradeable(want).balanceOf(address(this)).sub(_before);

            _deposit(earnedAfterFees);

            /// @dev Harvest event that every strategy MUST have, see BaseStrategy
            emit Harvest(earnedAfterFees, block.number);

            /// @dev Harvest must return the amount of want increased
            return earnedAfterFees;
        }
        return 0;
    }

    /// ===== Internal Helper Functions =====

    /// @dev used to manage the governance and strategist fee on earned rewards, make sure to use it to get paid!
    function _processRewardsFees(uint256 _amount, address _token)
        internal
    {
        if (performanceFeeGovernance > 0) {
            uint256 governanceRewardsFee = _processFee(
                _token,
                _amount,
                performanceFeeGovernance,
                IController(controller).rewards()
            );

            emit PerformanceFeeGovernance(
                IController(controller).rewards(),
                _token,
                governanceRewardsFee,
                block.number,
                block.timestamp
            );
        }

        if (performanceFeeStrategist > 0) {
            uint256 strategistRewardsFee = _processFee(
                _token,
                _amount,
                performanceFeeStrategist,
                strategist
            );

            emit PerformanceFeeStrategist(
                strategist,
                _token,
                strategistRewardsFee,
                block.number,
                block.timestamp
            );
        }
    }

    /// @dev View function for testing the routing of the strategy
    function findOptimalSwap(address tokenIn, address tokenOut, uint256 amountIn) external view returns (string memory, uint256 amount) {
        // Check Solidly
        (uint256 solidlyQuote, bool stable) = IBaseV1Router01(SOLIDLY_ROUTER).getAmountOut(amountIn, tokenIn, tokenOut);

        // Check Curve
        (, uint256 curveQuote) = ICurveRouter(CURVE_ROUTER).get_best_rate(tokenIn, tokenOut, amountIn);

        uint256 spookyQuote; // 0 by default

        // Check Spooky (Can Revert)
        address[] memory path = new address[](2);
        path[0] = address(tokenIn);
        path[1] = address(tokenOut);

        try IUniswapRouterV2(SPOOKY_ROUTER).getAmountsOut(amountIn, path) returns (uint256[] memory spookyAmounts) {
            spookyQuote = spookyAmounts[spookyAmounts.length - 1]; // Last one is the outToken
        } catch (bytes memory) {
            // We ignore as it means it's zero
        }

        
        // On average, we expect Solidly and Curve to offer better slippage
        // Spooky will be the default case
        if(solidlyQuote > spookyQuote) {
            // Either SOLID or curve
            if(curveQuote > solidlyQuote) {
                // Curve
                return ("curve", curveQuote);
            } else {
                // Solid 
                return ("SOLID", solidlyQuote);
            }

        } else if (curveQuote > spookyQuote) {
            // Curve is greater than both
            return ("curve", curveQuote);
        } else {
            // Spooky is best
            return ("spooky", spookyQuote);
        }
    }

    function _doOptimalSwap(address tokenIn, address tokenOut, uint256 amountIn) internal returns (uint256) {
       // Check Solidly
        (uint256 solidlyQuote, bool stable) = IBaseV1Router01(SOLIDLY_ROUTER).getAmountOut(amountIn, tokenIn, tokenOut);

        // Check Curve
        (, uint256 curveQuote) = ICurveRouter(CURVE_ROUTER).get_best_rate(tokenIn, tokenOut, amountIn);

        uint256 spookyQuote; // 0 by default

        // Check Spooky (Can Revert)
        address[] memory path = new address[](2);
        path[0] = address(tokenIn);
        path[1] = address(tokenOut);


        // NOTE: Ganache sometimes will randomly revert over this line, no clue why, you may need to comment this out for testing on forknet
        try SPOOKY_ROUTER.getAmountsOut(amountIn, path) returns (uint256[] memory spookyAmounts) {
            spookyQuote = spookyAmounts[spookyAmounts.length - 1]; // Last one is the outToken
        } catch (bytes memory) {
            // We ignore as it means it's zero
        }
        
        // On average, we expect Solidly and Curve to offer better slippage
        // Spooky will be the default case
        // Because we got quotes, we add them as min, but they are not guarantees we'll actually not get rekt
        if(solidlyQuote > spookyQuote) {
            // Either SOLID or curve
            if(curveQuote > solidlyQuote) {
                // Curve swap here
                return CURVE_ROUTER.exchange_with_best_rate(tokenIn, tokenOut, amountIn, curveQuote);
            } else {
                // Solid swap here
                route[] memory _route = new route[](1);
                _route[0] = route(tokenIn, tokenOut, stable);
                uint256[] memory amounts = SOLIDLY_ROUTER.swapExactTokensForTokens(amountIn, solidlyQuote, _route, address(this), now);
                return amounts[amounts.length - 1];
            }

        } else if (curveQuote > spookyQuote) {
            // Curve Swap here
            return CURVE_ROUTER.exchange_with_best_rate(tokenIn, tokenOut, amountIn, curveQuote);
        } else {
            // Spooky swap here
            uint256[] memory amounts = SPOOKY_ROUTER.swapExactTokensForTokens(
                amountIn,
                spookyQuote, // This is not a guarantee of anything beside the quote we already got, if we got frontrun we're already rekt here
                path,
                address(this),
                now
            ); // Btw, if you're frontrunning us on this contract, email me at alex@badger.finance we have actual money for you to make

            return amounts[amounts.length - 1];
        }
    }

}
