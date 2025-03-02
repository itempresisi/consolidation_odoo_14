# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ConsolidationAccount(models.Model):
    _name = 'consolidation.account'
    _description = 'Consolidation Account'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    group_id = fields.Many2one('consolidation.group', string='Consolidation Group', required=True)
    account_type = fields.Selection([
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expense')
    ], string='Account Type', required=True)
    is_intercompany = fields.Boolean(string='Is Intercompany Account')
    elimination_rule = fields.Selection([
        ('none', 'No Elimination'),
        ('full', 'Full Elimination'),
        ('proportional', 'Proportional Elimination')
    ], string='Elimination Rule', default='none')
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('unique_code_per_group', 'unique(code, group_id)', 'Account code must be unique per consolidation group!')
    ]


class ConsolidationAccountMapping(models.Model):
    _name = 'consolidation.account.mapping'
    _description = 'Account Mapping for Consolidation'
    
    group_id = fields.Many2one('consolidation.group', string='Consolidation Group', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    source_account_id = fields.Many2one('account.account', string='Source Account',
                                       domain="[('company_id', '=', company_id)]", required=True)
    source_account_code = fields.Char(related='source_account_id.code', string='Source Account Code', store=True)
    target_account_id = fields.Many2one('consolidation.account', string='Target Consolidation Account',
                                       domain="[('group_id', '=', group_id)]", required=True)
    conversion_method = fields.Selection([
        ('spot', 'Spot Rate'),
        ('average', 'Average Rate'),
        ('historical', 'Historical Rate'),
    ], string='Currency Conversion Method', default='spot', required=True)
    
    _sql_constraints = [
        ('unique_mapping', 'unique(group_id, company_id, source_account_id)', 
         'Each source account can only be mapped once per company in a consolidation group!')
    ]