# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class IntercompanyRelation(models.Model):
    _name = 'consolidation.intercompany.relation'
    _description = 'Intercompany Relation'
    
    group_id = fields.Many2one('consolidation.group', string='Consolidation Group', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    partner_company_id = fields.Many2one('res.company', string='Partner Company', required=True)
    account_id = fields.Many2one('account.account', string='Account', 
                                domain="[('company_id', '=', company_id)]", required=True)
    partner_account_id = fields.Many2one('account.account', string='Partner Account',
                                        domain="[('company_id', '=', partner_company_id)]", required=True)
    
    _sql_constraints = [
        ('unique_intercompany_relation', 'unique(group_id, company_id, partner_company_id, account_id)', 
         'This intercompany relation already exists!')
    ]


class AutomaticElimination(models.Model):
    _name = 'consolidation.automatic.elimination'
    _description = 'Automatic Intercompany Elimination'
    
    name = fields.Char(string='Name', required=True)
    group_id = fields.Many2one('consolidation.group', string='Consolidation Group', required=True)
    elimination_type = fields.Selection([
        ('investment', 'Investment in Subsidiary'),
        ('intercompany_balance', 'Intercompany Balance'),
        ('intercompany_profit', 'Intercompany Profit'),
        ('dividend', 'Intercompany Dividend')
    ], string='Elimination Type', required=True)
    active = fields.Boolean(default=True)
    
    company_id = fields.Many2one('res.company', string='Company')
    partner_company_id = fields.Many2one('res.company', string='Partner Company')
    
    account_mapping_ids = fields.One2many('consolidation.elimination.account.mapping', 'elimination_id', 
                                         string='Account Mappings for Elimination')
    
    def action_apply_elimination(self, period_id):
        elimination_journal = self.env['consolidation.journal'].search([
            ('period_id', '=', period_id),
            ('journal_type', '=', 'elimination')
        ], limit=1)
        
        if not elimination_journal:
            raise UserError(_('Elimination journal not found for this period.'))
        
        # Implementation would depend on the elimination type
        if self.elimination_type == 'investment':
            self._process_investment_elimination(elimination_journal)
        elif self.elimination_type == 'intercompany_balance':
            self._process_intercompany_balance_elimination(elimination_journal)
        # Other elimination types...
        
        return True
    
    def _process_investment_elimination(self, elimination_journal):
        # Implement investment elimination logic
        pass
    
    def _process_intercompany_balance_elimination(self, elimination_journal):
        # Implement intercompany balance elimination logic
        pass


class EliminationAccountMapping(models.Model):
    _name = 'consolidation.elimination.account.mapping'
    _description = 'Elimination Account Mapping'
    
    elimination_id = fields.Many2one('consolidation.automatic.elimination', string='Elimination Rule',
                                    required=True, ondelete='cascade')
    company_account_id = fields.Many2one('consolidation.account', string='Company Account')
    partner_account_id = fields.Many2one('consolidation.account', string='Partner Account')
    elimination_account_id = fields.Many2one('consolidation.account', string='Elimination Account')


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    is_intercompany = fields.Boolean(string='Is Intercompany Transaction', default=False)
    intercompany_partner_id = fields.Many2one('res.company', string='Intercompany Partner')