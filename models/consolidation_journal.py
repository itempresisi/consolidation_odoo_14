# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ConsolidationJournal(models.Model):
    _name = 'consolidation.journal'
    _description = 'Consolidation Journal'
    
    name = fields.Char(string='Name', required=True)
    period_id = fields.Many2one('consolidation.period', string='Consolidation Period', required=True)
    journal_type = fields.Selection([
        ('extraction', 'Data Extraction'),
        ('adjustment', 'Manual Adjustment'),
        ('elimination', 'Intercompany Elimination'),
        ('currency', 'Currency Translation'),
        ('reclassification', 'Reclassification')
    ], string='Journal Type', required=True)
    company_id = fields.Many2one('res.company', string='Related Company')
    line_ids = fields.One2many('consolidation.journal.line', 'journal_id', string='Journal Lines')
    
    @api.constrains('journal_type', 'company_id')
    def _check_company_for_extraction(self):
        for journal in self:
            if journal.journal_type == 'extraction' and not journal.company_id:
                raise ValidationError(_('Company is required for data extraction journals.'))


class ConsolidationJournalLine(models.Model):
    _name = 'consolidation.journal.line'
    _description = 'Consolidation Journal Line'
    
    journal_id = fields.Many2one('consolidation.journal', string='Journal', required=True, ondelete='cascade')
    name = fields.Char(string='Label', required=True)
    account_id = fields.Many2one('consolidation.account', string='Consolidation Account', required=True)
    debit = fields.Float(string='Debit', default=0.0)
    credit = fields.Float(string='Credit', default=0.0)
    company_id = fields.Many2one('res.company', string='Related Company')
    partner_company_id = fields.Many2one('res.company', string='Partner Company',
                                        help='Used for intercompany eliminations')
    
    @api.constrains('debit', 'credit')
    def _check_debit_credit(self):
        for line in self:
            if line.debit < 0 or line.credit < 0:
                raise ValidationError(_('Debit and credit amounts cannot be negative.'))