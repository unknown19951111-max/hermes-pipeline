"""
Harness generation — creates Chimera-compatible invariant test harnesses for fuzzing.
"""

import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional


class HarnessError(Exception):
    pass


class HarnessGenerator:
    """
    Generates or adapts Chimera-compatible invariant test harnesses.
    
    The harness wraps the target contract with the selected invariants
    and ensures compatibility with Medusa/Echidna assertion-mode testing.
    """

    def __init__(self, work_dir: str):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    INCOMPATIBLE_INVARIANTS: dict[str, str] = {
        "lending": "Lending health factor invariant not yet implemented — requires protocol-specific collateral ratio tracking",
        "dex_amm": "DEX constant product invariant not yet implemented — requires getReserves() integration",
        "governance": "Governance vote snapshot invariant not yet implemented — requires proposal flow integration",
        "bridge": "Bridge mint-bound invariant not yet implemented — requires cross-chain balance tracking",
    }

    def generate_harness(self, target_dir: str, archetype: str,
                         invariant_ids: list[str],
                         contract_name: str = "Contract") -> tuple[bool, str, str]:
        """
        Generate a Chimera-compatible invariant test harness.
        
        Returns: (success, harness_path, error_message)
        """
        # Check if the archetype has any implementable invariants
        if archetype in self.INCOMPATIBLE_INVARIANTS:
            return (
                False,
                "",
                f"INCOMPATIBLE_INVARIANT: {self.INCOMPATIBLE_INVARIANTS[archetype]}"
            )
        # Build the harness file
        harness_content = self._build_harness_content(
            archetype, invariant_ids, contract_name
        )
        
        # Write to target directory
        harness_path = Path(target_dir) / "test" / f"InvariantTest.t.sol"
        harness_path.parent.mkdir(parents=True, exist_ok=True)
        harness_path.write_text(harness_content)
        
        # Try to compile the harness
        success, error = self._verify_compilation(target_dir)
        
        return success, str(harness_path), error

    def _build_harness_content(self, archetype: str, invariant_ids: list[str],
                                contract_name: str) -> str:
        """Build the Solidity harness file content."""
        
        # Base harness template
        harness = f"""// SPDX-License-Identifier: MIT
pragma solidity >=0.8.0;

import "forge-std/Test.sol";
import "../src/{contract_name}.sol";

/**
 * @title InvariantTest
 * @notice Auto-generated Chimera-compatible invariant test harness.
 * 
 * Archetype: {archetype}
 * Invariants: {', '.join(invariant_ids)}
 * Generator version: 0.1.0
 */
contract InvariantTest is Test {{
    {contract_name} public target;
    
    // Handler state
    address[] public users;
    uint256 public constant MAX_USERS = 5;
    
    /// @dev Setup — deploy target and configure handler
    function setUp() public {{
        target = new {contract_name}();
        
        // Create test users
        for (uint256 i = 0; i < MAX_USERS; i++) {{
            address user = address(uint160(uint256(keccak256(abi.encode(i)))));
            users.push(user);
            vm.deal(user, 100 ether);
        }}
    }}

    // ===== Ghost Variables =====
    // Track cumulative state for invariant checks
    uint256 public ghost_totalSupply;
    mapping(address => uint256) public ghost_balances;
    
"""
        
        # Add archetype-specific invariants
        harness += self._get_archetype_invariants(archetype, contract_name)
        
        # Add handler functions
        harness += self._get_handler_functions(archetype, contract_name)
        
        harness += "}\n"
        
        return harness

    def _get_archetype_invariants(self, archetype: str, contract_name: str) -> str:
        """Get invariant assertion functions for the given archetype."""
        invariants = ""
        
        if archetype == "erc20" or archetype == "erc4626":
            invariants += """    /// @dev Invariant: total supply must equal sum of all balances
    function invariant_totalSupply() public {
        uint256 totalBal;
        for (uint256 i = 0; i < users.length; i++) {
            totalBal += target.balanceOf(users[i]);
        }
        // Also check the contract address
        totalBal += target.balanceOf(address(target));
        totalBal += target.balanceOf(address(this));
        assertEq(target.totalSupply(), totalBal, "totalSupply != sum(balances)");
    }
    
"""
        if archetype == "erc4626":
            invariants += """    /// @dev Invariant: totalAssets must reflect actual asset balance
    function invariant_totalAssets() public {
        // totalAssets must be >= any user's shares converted to assets
        if (target.balanceOf(address(this)) > 0) {
            uint256 minAssets = target.convertToShares(target.balanceOf(address(this)));
            assertGe(target.totalAssets(), minAssets, "totalAssets < minimum expected");
        }
    }
    
"""
        if archetype == "lending":
            invariants += """    /// @dev Invariant: health factor must be > 1 for all positions
    function invariant_healthFactor() public {
        // Lending-specific health check — requires protocol-specific implementation
        // Each borrowing position must maintain collateral ratio
    }
    
"""
        if archetype == "dex_amm":
            invariants += """    /// @dev Invariant: constant product (x*y=k) must hold
    function invariant_constantProduct() public {
        // DEX-specific check — requires getReserves() implementation
    }
    
"""
        if archetype == "governance":
            invariants += """    /// @dev Invariant: vote weight must be snapshot-protected
    function invariant_voteSnapshot() public {
        // Governance-specific check — requires proposal flow
    }
    
"""
        if archetype == "bridge":
            invariants += """    /// @dev Invariant: total minted must not exceed total locked
    function invariant_mintBound() public {
        // Bridge-specific check — requires cross-chain balance tracking
    }
    
"""
        return invariants

    def _get_handler_functions(self, archetype: str, contract_name: str) -> str:
        """Get handler functions for the given archetype."""
        # Generic handlers that work with any contract
        handlers = """    // ===== Handlers =====
    
    /// @dev Handler: call any function on the target
    /// @param fnSelector The function selector
    /// @param data The encoded call data
    function handler_call(bytes4 fnSelector, bytes calldata data) public {
        (bool success, ) = address(target).call(abi.encodePacked(fnSelector, data));
        // Don't assert — reverts are valid
        assembly { if iszero(success) { revert(0, 0) } }
    }
    
    /// @dev Handler: send ETH to the target
    function handler_deposit() public payable {
        // Call the target's deposit/fallback with ETH
        // This is a generic handler — specific contracts may need custom handlers
    }
    
"""
        return handlers

    def _verify_compilation(self, target_dir: str) -> tuple[bool, str]:
        """Verify that the generated harness compiles with forge build."""
        try:
            result = subprocess.run(
                ["forge", "build", "--via-ir", "--force"],
                cwd=target_dir,
                capture_output=True, text=True,
                timeout=120,
            )
            if result.returncode == 0:
                return True, ""
            else:
                return False, result.stderr[:500] + result.stdout[-500:]
        except subprocess.TimeoutExpired:
            return False, "BUILD TIMEOUT"
        except FileNotFoundError:
            return False, "forge not found in PATH"

    def check_compatibility(self, target_dir: str, invariant_ids: list[str],
                             compiler_version: str = "0.8.20") -> tuple[bool, list[str]]:
        """
        Check if the target is compatible with the selected invariants.
        
        Returns: (compatible, [reasons])
        """
        reasons = []
        
        # Check if target compiles
        try:
            result = subprocess.run(
                ["forge", "build", "--via-ir"],
                cwd=target_dir,
                capture_output=True, text=True,
                timeout=60,
            )
            if result.returncode != 0:
                reasons.append(f"Target does not compile: {result.stderr[:200]}")
        except FileNotFoundError:
            reasons.append("forge not found in PATH")
        except subprocess.TimeoutExpired:
            reasons.append("Build timed out")
        
        # Check for test directory
        test_dir = Path(target_dir) / "test"
        if not test_dir.exists():
            # Try to create it
            test_dir.mkdir(exist_ok=True)
        
        return len(reasons) == 0, reasons