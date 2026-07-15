// Known-positive Solana fixture: missing signer check
use anchor_lang::prelude::*;

declare_id!("Fg6Gfxsw1F8TjWQJCD5oRqG7CuJbKEnQY9H5kQp4pTn");

#[program]
pub mod vulnerable_solana {
    use super::*;
    // Vulnerable: no signer check on authority
    pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
        let vault = &mut ctx.accounts.vault;
        **vault.to_account_info().lamports.borrow_mut() -= amount;
        **ctx.accounts.recipient.to_account_info().lamports.borrow_mut() += amount;
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Withdraw {
    pub vault: Account<'info, Vault>,
    /// CHECK: Missing signer check — anyone can call withdraw
    pub authority: AccountInfo<'info>,
    pub recipient: AccountInfo<'info>,
}

#[account]
pub struct Vault {
    pub owner: Pubkey,
    pub balance: u64,
}
