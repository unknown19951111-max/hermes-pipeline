// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PatchedVault
 * @notice Patched version of VulnerableVault — uses checks-effects-interactions pattern.
 *         Slither should NOT flag the reentrancy-eth detector on this version.
 */
contract PatchedVault {
    mapping(address => uint256) public balances;

    event Deposited(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);

    constructor() {}

    function deposit() external payable {
        require(msg.value > 0, "Amount must be > 0");
        balances[msg.sender] += msg.value;
        emit Deposited(msg.sender, msg.value);
    }

    function withdraw(uint256 amount) external {
        require(amount > 0, "Amount must be > 0");
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // PATCH: checks-effects-interactions pattern
        // State update happens BEFORE external call
        balances[msg.sender] -= amount;

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        emit Withdrawn(msg.sender, amount);
    }

    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }
}