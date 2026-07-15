"""
Protocol-archetype classifier — determines protocol type from contract source evidence.

Uses deterministic rule-based classification from Slither AST, inheritance,
function signatures, and state variable analysis. LLM fallback is strictly
gated behind deterministic validation.
"""

import json
import re
import uuid
from pathlib import Path
from typing import Optional


class ClassifierError(Exception):
    pass


class ArchetypeEvidence:
    """Machine-readable evidence for an archetype classification."""

    def __init__(self, archetype: str, confidence: float,
                 evidence_signals: list[str], conflicts: list[str],
                 supporting_contracts: list[str],
                 detection_method: str):
        self.archetype = archetype
        self.confidence = confidence
        self.evidence_signals = evidence_signals
        self.conflicts = conflicts
        self.supporting_contracts = supporting_contracts
        self.detection_method = detection_method

    def to_dict(self) -> dict:
        return {
            "archetype": self.archetype,
            "confidence": self.confidence,
            "evidence_signals": self.evidence_signals,
            "conflicts": self.conflicts,
            "supporting_contracts": self.supporting_contracts,
            "detection_method": self.detection_method,
        }


class ProtocolClassifier:
    """
    Deterministic protocol-archetype classifier.
    
    Uses Solidity source analysis (AST patterns, inheritance, function signatures,
    state variables, modifiers, external calls, events) to classify contracts into
    known archetypes.
    """

    # Interface/inheritance signatures for archetype detection
    ARCHETYPE_SIGNATURES = {
        "erc20": {
            "interfaces": ["IERC20", "ERC20", "IERC20Metadata"],
            "functions": ["totalSupply()", "balanceOf(", "transfer(", "allowance("],
            "events": ["Transfer(", "Approval("],
            "state_vars": ["_balances", "_allowances", "_totalSupply"],
        },
        "erc721": {
            "interfaces": ["IERC721", "ERC721", "IERC721Metadata", "ERC721Enumerable"],
            "functions": ["ownerOf(", "tokenURI(", "safeTransferFrom("],
            "events": ["Transfer(", "Approval(", "ApprovalForAll("],
            "state_vars": ["_owners", "_balances"],
        },
        "erc1155": {
            "interfaces": ["IERC1155", "ERC1155", "IERC1155MetadataURI"],
            "functions": ["balanceOf(", "balanceOfBatch(", "safeTransferFrom("],
            "events": ["TransferSingle(", "TransferBatch(", "URI("],
        },
        "erc4626": {
            "interfaces": ["IERC4626", "ERC4626"],
            "functions": ["asset(", "totalAssets(", "convertToShares(", "deposit(", "redeem("],
            "events": ["Deposit(", "Withdraw("],
            "state_vars": ["_asset", "_totalAssets"],
        },
        "lending": {
            "functions": ["borrow(", "repay(", "liquidate(", "getAccountLiquidity("],
            "state_vars": ["borrowRate", "supplyRate", "totalBorrows", "totalReserves"],
            "patterns": ["utilizationRate", "healthFactor", "collateralFactor"],
        },
        "dex_amm": {
            "functions": ["swap(", "addLiquidity(", "removeLiquidity(", "getReserves("],
            "state_vars": ["reserve0", "reserve1", "totalSupply"],
            "patterns": ["kLast", "price0CumulativeLast", "sqrt("],
        },
        "staking": {
            "functions": ["stake(", "unstake(", "claimRewards(", "getReward("],
            "state_vars": ["_stakedBalances", "_rewards", "_lastUpdateTime"],
            "events": ["Staked(", "Unstaked(", "RewardsClaimed("],
        },
        "governance": {
            "interfaces": ["IGovernor", "Governor"],
            "functions": ["propose(", "vote(", "execute(", "queue("],
            "state_vars": ["proposalCount", "votingDelay", "votingPeriod"],
            "events": ["ProposalCreated(", "VoteCast(", "ProposalExecuted("],
        },
        "bridge": {
            "functions": ["mint(", "burn(", "sendMessage(", "processMessage("],
            "state_vars": ["nonce", "_messageCount"],
            "events": ["MessageSent(", "MessageReceived("],
            "patterns": ["merkleRoot", "signatureVerification", "vault"],
        },
        "oracle": {
            "functions": ["getPrice(", "getRate(", "consult(", "peek("],
            "state_vars": ["priceFeed", "lastUpdated"],
            "patterns": ["oracle", "aggregator", "sequencer"],
        },
        "proxy": {
            "patterns": ["delegatecall", "DELEGATECALL"],
            "functions": ["upgradeTo(", "upgradeToAndCall(", "implementation("],
            "interfaces": ["UUPS", "TransparentUpgradeableProxy"],
            "state_vars": ["_implementation", "_admin"],
        },
        "escrow": {
            "functions": ["deposit(", "release(", "refund(", "escrow("],
            "events": ["Deposited(", "Released(", "Refunded("],
            "state_vars": ["_deposits", "_released"],
        },
        "liquidation": {
            "patterns": ["liquidationCall", "liquidateBorrow", "auction"],
            "functions": ["startAuction(", "bid(", "claimCollateral("],
            "state_vars": ["_auctions", "_collateral"],
            "events": ["AuctionStarted(", "AuctionEnded("],
        },
        "rewards": {
            "functions": ["distributeRewards(", "claim(", "harvest("],
            "patterns": ["rewardPerToken", "earned(", "rewardRate"],
            "events": ["RewardDistributed(", "Harvested("],
        },
    }

    # Archetype→Invariant mapping
    ARCHETYPE_INVARIANTS = {
        "erc20": [
            "erc20-total-supply-invariant",
            "erc20-balance-invariant",
            "erc20-allowance-invariant",
        ],
        "erc721": [
            "erc721-total-supply-invariant",
            "erc721-balance-invariant",
            "erc721-owner-invariant",
        ],
        "erc4626": [
            "erc4626-total-assets-invariant",
            "erc4626-convert-to-shares-invariant",
            "erc4626-convert-to-assets-invariant",
            "erc4626-deposit-mint-invariant",
            "erc4626-withdraw-redeem-invariant",
        ],
        "lending": [
            "lending-health-factor-invariant",
            "lending-borrow-invariant",
            "lending-repay-invariant",
        ],
        "dex_amm": [
            "dex-k-constant-invariant",
            "dex-mint-burn-invariant",
            "dex-swap-fee-invariant",
        ],
        "staking": [
            "staking-balance-invariant",
            "staking-reward-invariant",
        ],
        "governance": [
            "governance-vote-weight-invariant",
            "governance-proposal-invariant",
        ],
        "bridge": [
            "bridge-mint-backed-by-collateral",
            "bridge-signature-set-validation",
        ],
        "proxy": [
            "proxy-implementation-invariant",
        ],
        "oracle": [
            "oracle-price-freshness-invariant",
        ],
        "liquidation": [
            "liquidation-seize-invariant",
        ],
    }

    def __init__(self):
        self.evidence_cache = {}

    def classify_from_slither(self, slither_output: dict, 
                              contracts: list[dict]) -> list[dict]:
        """
        Classify protocol archetypes from Slither analyzer output.
        
        Args:
            slither_output: Raw Slither JSON output (or parsed)
            contracts: List of contract info dicts with fields:
                - name: contract name
                - inheritance: list of inherited contracts/interfaces
                - functions: list of function signatures
                - state_variables: list of state variable names
                - events: list of event signatures
                - source: source file path
        
        Returns:
            List of classification results with archetype, confidence, evidence
        """
        classifications = []
        
        for contract in contracts:
            result = self._classify_contract(contract)
            classifications.append(result)
        
        return classifications

    def _classify_contract(self, contract: dict) -> dict:
        """Classify a single contract against all known archetypes."""
        name = contract.get("name", "Unknown")
        inheritance = [s.lower() for s in contract.get("inheritance", [])]
        functions = [s.lower() for s in contract.get("functions", [])]
        state_vars = [s.lower() for s in contract.get("state_variables", [])]
        events = [s.lower() for s in contract.get("events", [])]
        patterns = [s.lower() for s in contract.get("patterns", contract.get("code_patterns", []))]
        
        scores = {}
        all_evidence = {}
        
        for archetype, sigs in self.ARCHETYPE_SIGNATURES.items():
            score = 0.0
            evidence_signals = []
            
            # Check interface/inheritance matches
            for iface in sigs.get("interfaces", []):
                if iface.lower() in inheritance:
                    score += 25.0
                    evidence_signals.append(f"inherits {iface}")
            
            # Check function signature matches
            for func in sigs.get("functions", []):
                func_lower = func.lower()
                for f in functions:
                    if func_lower.split("(")[0] in f:
                        score += 10.0
                        evidence_signals.append(f"function: {func}")
                        break
            
            # Check event matches
            for evt in sigs.get("events", []):
                evt_lower = evt.lower().split("(")[0]
                for e in events:
                    if evt_lower in e:
                        score += 8.0
                        evidence_signals.append(f"event: {evt}")
                        break
            
            # Check state variable matches
            for var in sigs.get("state_vars", []):
                var_lower = var.lower().lstrip("_")
                for v in state_vars:
                    if var_lower in v.lower():
                        score += 5.0
                        evidence_signals.append(f"state_var: {var}")
                        break
            
            # Check pattern matches
            for ptn in sigs.get("patterns", []):
                ptn_lower = ptn.lower()
                if any(ptn_lower in p for p in patterns) or any(ptn_lower in f for f in functions):
                    score += 10.0
                    evidence_signals.append(f"pattern: {ptn}")
            
            if score > 0:
                scores[archetype] = score
                all_evidence[archetype] = evidence_signals
        
        # Determine winner and confidence
        if not scores:
            return {
                "contract": name,
                "classification": "unclassified",
                "confidence": 0.0,
                "evidence_signals": [],
                "conflicts": ["No archetype signatures matched"],
                "matched_archetypes": [],
                "detection_method": "rule_based",
            }
        
        sorted_archetypes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        winner = sorted_archetypes[0]
        
        # Calculate confidence from score profile
        total_score = sum(s[1] for s in sorted_archetypes[:3])
        confidence = min(1.0, winner[1] / max(total_score, 1))
        
        # Detect conflicts (close second place)
        conflicts = []
        if len(sorted_archetypes) > 1:
            second = sorted_archetypes[1]
            if second[1] >= winner[1] * 0.7:
                conflicts.append(f"Ambiguous: {second[0]} at {second[1]:.0f} vs {winner[0]} at {winner[1]:.0f}")
        
        # Multi-label support — include any archetype above threshold
        matched = []
        for name, score_val in sorted_archetypes:
            if score_val >= winner[1] * 0.5:
                matched.append({
                    "archetype": name,
                    "score": score_val,
                    "confidence": min(1.0, score_val / max(total_score, 1)),
                })
        
        return {
            "contract": contract.get("name", "Unknown"),
            "classification": winner[0],
            "confidence": confidence,
            "evidence_signals": all_evidence.get(winner[0], []),
            "conflicts": conflicts,
            "matched_archetypes": matched,
            "detection_method": "rule_based",
        }

    def classify_from_source(self, source_dir: str) -> list[dict]:
        """
        Fallback classification using source file analysis.
        Scans .sol files for patterns without Slither.
        """
        path = Path(source_dir)
        sol_files = list(path.rglob("*.sol"))
        classifications = []
        
        for sol_file in sol_files:
            try:
                content = sol_file.read_text()
                
                # Extract interface names
                inherits = re.findall(r'is\s+([A-Za-z0-9_,\s]+)', content)
                functions = re.findall(r'function\s+([A-Za-z0-9_]+)\s*\(', content)
                events = re.findall(r'event\s+([A-Za-z0-9_]+)\s*\(', content)
                state_vars = re.findall(r'(mapping|uint256|address|bool)\s+(public|internal|private)\s+([A-Za-z0-9_]+)', content)
                
                contract_match = re.search(r'contract\s+([A-Za-z0-9_]+)', content)
                contract_name = contract_match.group(1) if contract_match else sol_file.stem
                
                contract = {
                    "name": contract_name,
                    "inheritance": [i.strip() for i in inherits],
                    "functions": functions,
                    "events": events,
                    "state_variables": [v[2] for v in state_vars],
                    "patterns": [],
                }
                
                result = self._classify_contract(contract)
                result["source_file"] = str(sol_file)
                classifications.append(result)
                
            except Exception as e:
                classifications.append({
                    "contract": sol_file.stem,
                    "classification": "analysis_failure",
                    "confidence": 0.0,
                    "evidence_signals": [],
                    "conflicts": [f"Parse error: {e}"],
                    "matched_archetypes": [],
                    "detection_method": "source_analysis",
                    "source_file": str(sol_file),
                })
        
        return classifications

    def get_invariant_ids(self, archetype: str) -> list[str]:
        """Get the recommended invariant IDs for a given archetype."""
        return self.ARCHETYPE_INVARIANTS.get(archetype, [])

    def get_multi_label_invariant_ids(self, classifications: list[dict]) -> list[str]:
        """Get invariant IDs for a multi-label classification result."""
        invariants = set()
        for cls in classifications:
            archetype = cls.get("classification", "")
            archetype_invariants = self.get_invariant_ids(archetype)
            invariants.update(archetype_invariants)
            
            # Also check matched_archetypes for secondary matches
            for match in cls.get("matched_archetypes", []):
                secondary = match.get("archetype", "")
                if secondary != archetype:
                    invariants.update(self.get_invariant_ids(secondary))
        
        return list(invariants)