# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ConsolidationAnalysis(models.Model):
    _name = 'consolidation.analysis'
    _description = 'Consolidation Analysis'
    
    name = fields.Char(string='Name', required=True)
    period_id = fields.Many2one('consolidation.period', string='Consolidation Period', required=True)
    analysis_type = fields.Selection([
        ('balance_sheet', 'Balance Sheet'),
        ('income', 'Income Statement'),
        ('cash_flow', 'Cash Flow Statement'),
        ('changes_equity', 'Changes in Equity'),
        ('custom', 'Custom Analysis')
    ], string='Analysis Type', default='balance_sheet', required=True)
    line_ids = fields.One2many('consolidation.analysis.line', 'analysis_id', string='Analysis Lines')
    
    def action_compute_analysis(self):
        self.ensure_one()
        
        # Clear existing lines
        self.line_ids.unlink()
        
        # Prepare accounts based on analysis type
        accounts = []
        if self.analysis_type == 'balance_sheet':
            accounts = self.env['consolidation.account'].search([
                ('group_id', '=', self.period_id.group_id.id),
                ('account_type', 'in', ['asset', 'liability', 'equity'])
            ])
        elif self.analysis_type == 'income':
            accounts = self.env['consolidation.account'].search([
                ('group_id', '=', self.period_id.group_id.id),
                ('account_type', 'in', ['income', 'expense'])
            ])
        # Add other types as needed
        
        # Create analysis lines
        for account in accounts:
            balance = self._get_account_balance(account)
            if balance != 0:
                self.env['consolidation.analysis.line'].create({
                    'analysis_id': self.id,
                    'account_id': account.id,
                    'amount': balance
                })
        
        return True
    
    def _get_account_balance(self, account):
        # Get all journal lines for this account in the period
        journal_lines = self.env['consolidation.journal.line'].search([
            ('journal_id.period_id', '=', self.period_id.id),
            ('account_id', '=', account.id)
        ])
        
        balance = 0.0
        for line in journal_lines:
            balance += line.debit - line.credit
        
        # Inverting balance based on account type for proper presentation
        if account.account_type in ['liability', 'equity', 'income']:
            balance = -balance
            
        return balance


class ConsolidationAnalysisLine(models.Model):
    _name = 'consolidation.analysis.line'
    _description = 'Consolidation Analysis Line'
    
    analysis_id = fields.Many2one('consolidation.analysis', string='Analysis', required=True, ondelete='cascade')
    account_id = fields.Many2one('consolidation.account', string='Consolidation Account', required=True)
    amount = fields.Float(string='Amount')


class ConsolidationReport(models.Model):
    _name = 'consolidation.report'
    _description = 'Consolidation Report'
    
    name = fields.Char(string='Name', required=True)
    period_id = fields.Many2one('consolidation.period', string='Consolidation Period', required=True)
    report_type = fields.Selection([
        ('balance_sheet', 'Balance Sheet'),
        ('income', 'Income Statement'),
        ('cash_flow', 'Cash Flow Statement'),
        ('changes_equity', 'Changes in Equity'),
        ('notes', 'Notes to Financial Statements')
    ], string='Report Type', default='balance_sheet', required=True)
    template_id = fields.Many2one('consolidation.report.template', string='Report Template')
    

class ConsolidationReportTemplate(models.Model):
    _name = 'consolidation.report.template'
    _description = 'Consolidation Report Template'
    
    name = fields.Char(string='Name', required=True)
    report_type = fields.Selection([
        ('balance_sheet', 'Balance Sheet'),
        ('income', 'Income Statement'),
        ('cash_flow', 'Cash Flow Statement'),
        ('changes_equity', 'Changes in Equity'),
        ('notes', 'Notes to Financial Statements')
    ], string='Report Type', default='balance_sheet', required=True)
    line_ids = fields.One2many('consolidation.report.template.line', 'template_id', string='Template Lines')


class ConsolidationReportTemplateLine(models.Model):
    _name = 'consolidation.report.template.line'
    _description = 'Consolidation Report Template Line'
    _order = 'sequence, id'
    
    template_id = fields.Many2one('consolidation.report.template', string='Report Template', required=True, ondelete='cascade')
    name = fields.Char(string='Line Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    line_type = fields.Selection([
        ('section', 'Section'),
        ('subsection', 'Subsection'),
        ('account', 'Account'),
        ('computation', 'Computation'),
        ('total', 'Total')
    ], string='Line Type', default='account', required=True)
    formula = fields.Char(string='Formula', help='Python expression to compute the line amount')
    account_ids = fields.Many2many('consolidation.account', string='Accounts')
    parent_id = fields.Many2one('consolidation.report.template.line', string='Parent Line')
    child_ids = fields.One2many('consolidation.report.template.line', 'parent_id', string='Child Lines')