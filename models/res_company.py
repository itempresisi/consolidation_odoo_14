# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    # Fields for consolidation settings
    consolidation_company = fields.Boolean(string='Is a Consolidation Company', default=False,
                                         help='Check this if the company is used for consolidation purposes only')
    parent_company_id = fields.Many2one('res.company', string='Parent Company',
                                       help='The parent company in the group structure')
    child_company_ids = fields.One2many('res.company', 'parent_company_id', string='Subsidiaries')
    
    ownership_percentage = fields.Float(string='Ownership Percentage', default=100.0,
                                      help='Percentage of ownership by the parent company')
    consolidation_method = fields.Selection([
        ('full', 'Full Consolidation'),
        ('proportional', 'Proportional Consolidation'),
        ('equity', 'Equity Method'),
        ('not_consolidated', 'Not Consolidated')
    ], string='Default Consolidation Method', default='full')
    
    # Fields for tracking intercompany relationships
    consolidation_group_ids = fields.Many2many('consolidation.group', string='Consolidation Groups')
    
    @api.constrains('ownership_percentage')
    def _check_ownership_percentage(self):
        for company in self:
            if company.ownership_percentage < 0 or company.ownership_percentage > 100:
                raise ValueError(_('Ownership percentage must be between 0 and 100.'))