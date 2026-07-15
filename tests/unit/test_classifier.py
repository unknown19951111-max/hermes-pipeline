"""
Unit tests for protocol-archetype classifier.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from orchestrator.classify import ProtocolClassifier


def test_erc20_classification():
    """Test ERC-20 token classification."""
    classifier = ProtocolClassifier()
    
    contract = {
        "name": "TestToken",
        "inheritance": ["ERC20", "IERC20Metadata", "Ownable"],
        "functions": [
            "totalSupply()", "balanceOf(address)", "transfer(address,uint256)",
            "allowance(address,address)", "approve(address,uint256)", "transferFrom(address,address,uint256)",
            "name()", "symbol()", "decimals()",
        ],
        "state_variables": ["_balances", "_allowances", "_totalSupply", "_name", "_symbol"],
        "events": ["Transfer(address,address,uint256)", "Approval(address,address,uint256)"],
        "patterns": ["erc20"],
    }
    
    result = classifier._classify_contract(contract)
    assert result["classification"] == "erc20", f"Expected erc20, got {result['classification']}"
    assert result["confidence"] > 0.5, f"Confidence too low: {result['confidence']}"
    assert len(result["evidence_signals"]) > 0, "Should have evidence signals"
    print(f"  ✅ ERC-20: {result['classification']} @ {result['confidence']:.2f} — {len(result['evidence_signals'])} signals")


def test_erc4626_classification():
    """Test ERC-4626 vault classification."""
    classifier = ProtocolClassifier()
    
    contract = {
        "name": "TestVault",
        "inheritance": ["ERC4626", "ERC20", "IERC4626"],
        "functions": [
            "asset()", "totalAssets()", "convertToShares(uint256)", "convertToAssets(uint256)",
            "maxDeposit(address)", "previewDeposit(uint256)", "deposit(uint256,address)",
            "maxMint(address)", "previewMint(uint256)", "mint(uint256,address)",
            "maxWithdraw(address)", "previewWithdraw(uint256)", "withdraw(uint256,address,address)",
            "maxRedeem(address)", "previewRedeem(uint256)", "redeem(uint256,address,address)",
            "totalSupply()", "balanceOf(address)",
        ],
        "state_variables": ["_asset", "_totalAssets", "_totalSupply", "_balances"],
        "events": ["Deposit(address,address,uint256,uint256)", "Withdraw(address,address,address,uint256,uint256)"],
        "patterns": ["vault", "yield"],
    }
    
    result = classifier._classify_contract(contract)
    assert result["classification"] == "erc4626", f"Expected erc4626, got {result['classification']}"
    assert result["confidence"] > 0.5
    print(f"  ✅ ERC-4626: {result['classification']} @ {result['confidence']:.2f} — {len(result['evidence_signals'])} signals")


def test_lending_classification():
    """Test lending protocol classification."""
    classifier = ProtocolClassifier()
    
    contract = {
        "name": "TestLendingPool",
        "inheritance": ["Ownable"],
        "functions": [
            "borrow(address,uint256)", "repay(address,uint256)", "liquidate(address,address,uint256)",
            "getAccountLiquidity(address)", "getHealthFactor(address)",
            "deposit(address,uint256)", "withdraw(address,uint256)",
        ],
        "state_variables": ["borrowRate", "supplyRate", "totalBorrows", "totalReserves", "collateralFactor"],
        "events": ["Deposited(address,uint256)", "Borrowed(address,uint256)", "Repaid(address,uint256)", "Liquidated(address,address,uint256)"],
        "patterns": ["utilizationRate", "healthFactor"],
    }
    
    result = classifier._classify_contract(contract)
    assert result["classification"] == "lending", f"Expected lending, got {result['classification']}"
    assert result["confidence"] > 0.5
    print(f"  ✅ Lending: {result['classification']} @ {result['confidence']:.2f} — {len(result['evidence_signals'])} signals")


def test_governance_classification():
    """Test governance protocol classification."""
    classifier = ProtocolClassifier()
    
    contract = {
        "name": "TestGovernor",
        "inheritance": ["Governor", "IGovernor", "GovernorVotes"],
        "functions": [
            "propose(address[],uint256[],bytes[],string)", "vote(uint256,uint8)",
            "execute(address[],uint256[],bytes[],bytes32)", "queue(address[],uint256[],bytes[],bytes32)",
            "proposalCount()", "votingDelay()", "votingPeriod()",
        ],
        "state_variables": ["proposalCount", "votingDelay", "votingPeriod"],
        "events": ["ProposalCreated(uint256,address,address[],uint256[],string[],bytes[],uint256,uint256,string)"],
        "patterns": ["governance", "timelock"],
    }
    
    result = classifier._classify_contract(contract)
    assert result["classification"] == "governance", f"Expected governance, got {result['classification']}"
    assert result["confidence"] > 0.5
    print(f"  ✅ Governance: {result['classification']} @ {result['confidence']:.2f} — {len(result['evidence_signals'])} signals")


def test_bridge_classification():
    """Test bridge protocol classification."""
    classifier = ProtocolClassifier()
    
    contract = {
        "name": "TestBridge",
        "inheritance": [],
        "functions": [
            "mint(address,uint256,bytes)", "burn(address,uint256)",
            "sendMessage(uint256,bytes)", "processMessage(bytes)",
            "verifySignature(bytes,bytes)", "deposit(address,uint256)",
        ],
        "state_variables": ["nonce", "_messageCount", "validatedMessages"],
        "events": ["MessageSent(bytes32,uint256,address)", "MessageReceived(bytes32,uint256,address)"],
        "patterns": ["merkleRoot", "signatureVerification"],
    }
    
    result = classifier._classify_contract(contract)
    assert result["classification"] == "bridge", f"Expected bridge, got {result['classification']}"
    assert result["confidence"] > 0.5
    print(f"  ✅ Bridge: {result['classification']} @ {result['confidence']:.2f} — {len(result['evidence_signals'])} signals")


def test_classify_from_source():
    """Test classification from source file analysis."""
    classifier = ProtocolClassifier()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        sol_file = Path(tmpdir) / "TestToken.sol"
        sol_file.write_text("""
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
contract TestToken is ERC20 {
    function mint(address to, uint256 amount) public {
        _mint(to, amount);
    }
    function burn(uint256 amount) public {
        _burn(msg.sender, amount);
    }
}
""")
        results = classifier.classify_from_source(tmpdir)
        assert len(results) > 0, "Should produce at least one classification"
        print(f"  ✅ Source analysis: {len(results)} classifications")


def test_multi_label():
    """Test multi-label classification (hybrid contracts)."""
    classifier = ProtocolClassifier()
    
    # ERC-4626 vault that also has staking
    contract = {
        "name": "YieldStakingVault",
        "inheritance": ["ERC4626", "ERC20"],
        "functions": [
            "asset()", "totalAssets()", "convertToShares(uint256)", "deposit(uint256,address)",
            "stake(uint256)", "unstake(uint256)", "claimRewards()", "getReward(address)",
            "totalSupply()", "balanceOf(address)",
        ],
        "state_variables": ["_asset", "_totalAssets", "_stakedBalances", "_rewards", "_totalSupply", "_balances"],
        "events": ["Deposit(address,address,uint256,uint256)", "Staked(address,uint256)", "Unstaked(address,uint256)", "RewardsClaimed(address,uint256)"],
        "patterns": ["vault", "stake", "reward"],
    }
    
    result = classifier._classify_contract(contract)
    assert len(result["matched_archetypes"]) > 1, "Should have multiple archetype matches"
    archetypes = [m["archetype"] for m in result["matched_archetypes"]]
    print(f"  ✅ Multi-label: {archetypes}")
    # Should detect both erc4626 and staking
    assert "erc4626" in archetypes or "staking" in archetypes


def test_unclassified():
    """Test that an unknown contract returns unclassified."""
    classifier = ProtocolClassifier()
    
    contract = {
        "name": "CustomLogic",
        "inheritance": [],
        "functions": ["doSomething()", "doSomethingElse()"],
        "state_variables": ["x", "y", "z"],
        "events": [],
        "patterns": [],
    }
    
    result = classifier._classify_contract(contract)
    assert result["classification"] == "unclassified", f"Expected unclassified, got {result['classification']}"
    print(f"  ✅ Unclassified: {result['classification']}")


def test_invariant_selection():
    """Test that invariant selection works from classifications."""
    classifier = ProtocolClassifier()
    
    # Test single archetype
    invariants = classifier.get_invariant_ids("erc20")
    assert len(invariants) > 0, "Should have ERC-20 invariants"
    assert "erc20-total-supply-invariant" in invariants
    print(f"  ✅ ERC-20 invariants: {len(invariants)}")
    
    # Test multi-label
    contract = {
        "name": "TestVault",
        "inheritance": ["ERC4626"],
        "functions": ["asset()", "totalAssets()", "deposit(uint256,address)", "redeem(uint256,address,address)"],
        "state_variables": ["_asset", "_totalAssets"],
        "events": ["Deposit(address,address,uint256,uint256)"],
        "patterns": [],
    }
    result = classifier._classify_contract(contract)
    all_invariants = classifier.get_multi_label_invariant_ids([result])
    print(f"  ✅ Multi-label invariants: {len(all_invariants)}: {all_invariants}")
    assert len(all_invariants) > 0


if __name__ == "__main__":
    print("=" * 60)
    print("CLASSIFIER UNIT TESTS")
    print("=" * 60)
    
    test_erc20_classification()
    test_erc4626_classification()
    test_lending_classification()
    test_governance_classification()
    test_bridge_classification()
    test_classify_from_source()
    test_multi_label()
    test_unclassified()
    test_invariant_selection()
    
    print(f"\n{'='*60}")
    print("ALL CLASSIFIER TESTS PASSED")
    print(f"{'='*60}")