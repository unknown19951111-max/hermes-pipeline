// Known-positive Move fixture: missing access control
module vulnerable_move::vulnerable_vault {
    use std::signer;
    use aptos_framework::coin;
    use aptos_framework::account;

    struct Vault has key {
        owner: address,
        balance: u64,
    }

    // Vulnerable: no signer verification against stored owner
    public fun withdraw(account: &signer, amount: u64) acquires Vault {
        let vault = borrow_global_mut<Vault>(@vulnerable_move);
        // Missing: assert!(signer::address_of(account) == vault.owner, 0);
        vault.balance = vault.balance - amount;
        // Transfer happens but access control is bypassed
    }

    public fun deposit(account: &signer, amount: u64) {
        let addr = signer::address_of(account);
        if (!exists<Vault>(@vulnerable_move)) {
            move_to(account, Vault { owner: addr, balance: 0 });
        };
        let vault = borrow_global_mut<Vault>(@vulnerable_move);
        vault.balance = vault.balance + amount;
    }
}
