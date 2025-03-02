# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class IntercompanyMatchingWizard(models.TransientModel):
    _name = 'consolidation.intercompany.matching.wizard'
    _description = 'Intercompany Transactions Matching Wizard'
    
    period_id = fields.Many2one('consolidation.period', string='Consolidation Period', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    partner_company_id = fields.Many2one('res.company', string='Partner Company', required=True)
    
    # Differences found after matching
    differences_found = fields.Boolean(string='Differences Found', compute='_compute_differences')
    difference_ids = fields.One2many('consolidation.intercompany.difference', 'wizard_id', string='Differences')
    
    @api.depends('company_id', 'partner_company_id', 'period_id')
    def _compute_differences(self):
        for wizard in self:
            wizard.differences_found = False
            wizard.difference_ids = [(5, 0, 0)]  # Clear existing records
            
            if not wizard.company_id or not wizard.partner_company_id or not wizard.period_id:
                continue
            
            # Find intercompany relations
            relations = self.env['consolidation.intercompany.relation'].search([
                ('group_id', '=', wizard.period_id.group_id.id),
                '|',
                '&', ('company_id', '=', wizard.company_id.id), ('partner_company_id', '=', wizard.partner_company_id.id),
                '&', ('company_id', '=', wizard.partner_company_id.id), ('partner_company_id', '=', wizard.company_id.id)
            ])
            
            # If no relations defined, we can't match
            if not relations:
                continue
            
            # Find the extraction journals for both companies
            company_journal = self.env['consolidation.journal'].search([
                ('period_id', '=', wizard.period_id.id),
                ('journal_type', '=', 'extraction'),
                ('company_id', '=', wizard.company_id.id)
            ], limit=1)
            
            partner_journal = self.env['consolidation.journal'].search([
                ('period_id', '=', wizard.period_id.id),
                ('journal_type', '=', 'extraction'),
                ('company_id', '=', wizard.partner_company_id.id)
            ], limit=1)
            
            if not company_journal or not partner_journal:
                continue
            
            # For each relation, check corresponding entries
            for relation in relations:
                # Get corresponding consolidated accounts
                company_account_mapping = self.env['consolidation.account.mapping'].search([
                    ('group_id', '=', wizard.period_id.group_id.id),
                    ('company_id', '=', wizard.company_id.id),
                    ('source_account_id', '=', relation.account_id.id if relation.company_id == wizard.company_id else relation.partner_account_id.id)
                ], limit=1)
                
                partner_account_mapping = self.env['consolidation.account.mapping'].search([
                    ('group_id', '=', wizard.period_id.group_id.id),
                    ('company_id', '=', wizard.partner_company_id.id),
                    ('source_account_id', '=', relation.partner_account_id.id if relation.company_id == wizard.company_id else relation.account_id.id)
                ], limit=1)
                
                if not company_account_mapping or not partner_account_mapping:
                    continue
                
                # Get the balance for each account in the consolidation journals
                company_balance = sum(self.env['consolidation.journal.line'].search([
                    ('journal_id', '=', company_journal.id),
                    ('account_id', '=', company_account_mapping.target_account_id.id)
                ]).mapped(lambda l: l.debit - l.credit))
                
                partner_balance = sum(self.env['consolidation.journal.line'].search([
                    ('journal_id', '=', partner_journal.id),
                    ('account_id', '=', partner_account_mapping.target_account_id.id)
                ]).mapped(lambda l: l.debit - l.credit))
                
                # For a matching intercompany entry, these should sum to zero
                # (partner's receivable + company's payable = 0)
                difference = company_balance + partner_balance
                
                # If there's a significant difference, record it
                if abs(difference) > 0.01:  # Using a small threshold to avoid floating point issues
                    wizard.difference_ids = [(0, 0, {
                        'company_id': wizard.company_id.id,
                        'partner_company_id': wizard.partner_company_id.id,
                        'company_account_id': company_account_mapping.target_account_id.id,
                        'partner_account_id': partner_account_mapping.target_account_id.id,
                        'company_balance': company_balance,
                        'partner_balance': partner_balance,
                        'difference': difference
                    })]
                    wizard.differences_found = True
    
    def action_create_adjustment_entries(self):
        self.ensure_one()
        
        if not self.differences_found or not self.difference_ids:
            raise UserError(_('No differences to adjust.'))
        
        # Find the adjustment journal
        adjustment_journal = self.env['consolidation.journal'].search([
            ('period_id', '=', self.period_id.id),
            ('journal_type', '=', 'adjustment')
        ], limit=1)
        
        if not adjustment_journal:
            adjustment_journal = self.env['consolidation.journal'].create({
                'name': _('Consolidation Adjustments'),
                'period_id': self.period_id.id,
                'journal_type': 'adjustment'
            })
        
        # Create adjustment entries for each difference
        for diff in self.difference_ids:
            # Only create adjustments for selected differences
            if not diff.apply_adjustment:
                continue
            
            # Create the adjustment entry
            # This is a simple approach - in practice, you'd need to decide which side to adjust
            # and potentially have a more sophisticated approach
            
            # Adjust the company side
            line_vals = {
                'journal_id': adjustment_journal.id,
                'name': _('Intercompany adjustment between %s and %s') % (
                    diff.company_id.name, diff.partner_company_id.name),
                'account_id': diff.company_account_id.id,
                'company_id': diff.company_id.id,
                'partner_company_id': diff.partner_company_id.id,
            }
            
            # If balance needs to increase
            if diff.adjustment_target == 'increase_company':
                line_vals.update({
                    'debit': abs(diff.difference),
                    'credit': 0.0
                })
            # If balance needs to decrease
            else:
                line_vals.update({
                    'debit': 0.0,
                    'credit': abs(diff.difference)
                })
            
            self.env['consolidation.journal.line'].create(line_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Adjustment Journal'),
            'res_model': 'consolidation.journal',
            'res_id': adjustment_journal.id,
            'view_mode': 'form',
            'target': 'current',
        }


class IntercompanyDifference(models.TransientModel):
    _name = 'consolidation.intercompany.difference'
    _description = 'Intercompany Balance Difference'
    
    wizard_id = fields.Many2one('consolidation.intercompany.matching.wizard', string='Wizard')
    company_id = fields.Many2one('res.company', string='Company')
    partner_company_id = fields.Many2one('res.company', string='Partner Company')
    company_account_id = fields.Many2one('consolidation.account', string='Company Account')
    partner_account_id = fields.Many2one('consolidation.account', string='Partner Account')
    company_balance = fields.Float(string='Company Balance')
    partner_balance = fields.Float(string='Partner Balance')
    difference = fields.Float(string='Difference')
    
    apply_adjustment = fields.Boolean(string='Apply Adjustment', default=True)
    adjustment_target = fields.Selection([
        ('increase_company', 'Increase Company Balance'),
        ('decrease_company', 'Decrease Company Balance'),
    ], string='Adjustment Target', default='increase_company')