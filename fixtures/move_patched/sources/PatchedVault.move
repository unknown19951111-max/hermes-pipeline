// Known-negative Move fixture: proper access control
module patched_move::patched_vault {
    use std::signer;
    use aptos_framework::coin;
    use aptos_framework::account;

    struct Vault has key {
        owner: address,
        balance: u64,
    }

    // Patched: owner check enforced
    public fun withdraw(account: &signer, amount: u64) acquires Vault {
        let vault = borrow_global_mut<Vault>(@patched_move);
        assert!(signer::address_of(account) == vault.owner, 0);
        vault.balance = vault.balance - amount;
    }

    public fun deposit(account: &signer, amount: u64) {
        let addr = signer::address_of(account);
        if (!exists<Vault>(@patched_move)) {
            move_to(account, Vault { owner: addr, balance: 0 });
        };
        let vault = borrow_global_mut<Vault>(@patched_move);
        vault.balance = vault.balance + amount;
    }
}
