// Known-negative Solana fixture: proper signer check
use anchor_lang::prelude::*;

declare_id!("Fg6Gfxsw1F8TjWQJCD5oRqG7CuJbKEnQY9H5kQp4pTn");

#[program]
pub mod patched_solana {
    use super::*;
    // Patched: authority must be a signer
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
    #[account(signer)]
    pub authority: Signer<'info>,
    pub recipient: AccountInfo<'info>,
}

#[account]
pub struct Vault {
    pub owner: Pubkey,
    pub balance: u64,
}
