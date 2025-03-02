# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ConsolidationGroup(models.Model):
    _name = 'consolidation.group'
    _description = 'Consolidation Group'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    company_ids = fields.Many2many('res.company', string='Companies', required=True)
    parent_company_id = fields.Many2one('res.company', string='Parent Company', required=True)
    currency_id = fields.Many2one('res.currency', string='Consolidation Currency', required=True)
    consolidation_method = fields.Selection([
        ('full', 'Full Consolidation'),
        ('proportional', 'Proportional Consolidation'),
        ('equity', 'Equity Method')
    ], string='Consolidation Method', default='full', required=True)
    threshold = fields.Float(string='Materiality Threshold (%)', default=1.0)
    active = fields.Boolean(default=True)
    
    mapping_ids = fields.One2many('consolidation.account.mapping', 'group_id', string='Account Mappings')
    period_ids = fields.One2many('consolidation.period', 'group_id', string='Consolidation Periods')
    
    @api.constrains('company_ids', 'parent_company_id')
    def _check_parent_in_companies(self):
        for group in self:
            if group.parent_company_id not in group.company_ids:
                raise ValidationError(_("Parent company must be included in the consolidation group companies."))