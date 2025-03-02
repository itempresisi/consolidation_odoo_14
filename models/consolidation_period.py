# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ConsolidationPeriod(models.Model):
    _name = 'consolidation.period'
    _description = 'Consolidation Period'
    _order = 'date_end desc'
    
    name = fields.Char(string='Name', required=True)
    group_id = fields.Many2one('consolidation.group', string='Consolidation Group', required=True)
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed')
    ], default='draft', string='Status')
    company_period_ids = fields.One2many('consolidation.company.period', 'period_id', string='Company Periods')
    journal_ids = fields.One2many('consolidation.journal', 'period_id', string='Consolidation Journals')
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for period in self:
            if period.date_start > period.date_end:
                raise ValidationError(_('Start date must be earlier than end date.'))
    
    @api.model
    def create(self, vals):
        period = super(ConsolidationPeriod, self).create(vals)
        # Automatically create company periods for each company in the group
        for company in period.group_id.company_ids:
            self.env['consolidation.company.period'].create({
                'period_id': period.id,
                'company_id': company.id,
                'state': 'draft'
            })
        return period
    
    def action_prepare_consolidation(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('You can only prepare consolidation for periods in draft state.'))
        
        # Set period to in progress
        self.write({'state': 'in_progress'})
        
        # Create analysis and comparison journals
        self.env['consolidation.journal'].create({
            'name': _('Consolidation Adjustments'),
            'period_id': self.id,
            'journal_type': 'adjustment'
        })
        
        self.env['consolidation.journal'].create({
            'name': _('Intercompany Eliminations'),
            'period_id': self.id,
            'journal_type': 'elimination'
        })
        
        self.env['consolidation.journal'].create({
            'name': _('Currency Translation'),
            'period_id': self.id,
            'journal_type': 'currency'
        })
        
        return True
    
    def action_close_period(self):
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('You can only close periods that are in progress.'))
        
        # Check if all company periods are completed
        incomplete_periods = self.company_period_ids.filtered(lambda p: p.state != 'completed')
        if incomplete_periods:
            company_names = ', '.join(incomplete_periods.mapped('company_id.name'))
            raise UserError(_('Cannot close period. The following companies have not completed their periods: %s') % company_names)
        
        # Close the period
        self.write({'state': 'closed'})
        return True
    
    def action_reopen_period(self):
        self.ensure_one()
        if self.state != 'closed':
            raise UserError(_('You can only reopen closed periods.'))
        
        self.write({'state': 'in_progress'})
        return True


class ConsolidationCompanyPeriod(models.Model):
    _name = 'consolidation.company.period'
    _description = 'Company Consolidation Period'
    
    period_id = fields.Many2one('consolidation.period', string='Consolidation Period', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], default='draft', string='Status')
    ownership_percentage = fields.Float(string='Ownership %', default=100.0)
    control_percentage = fields.Float(string='Control %', default=100.0)
    include_in_consolidation = fields.Boolean(string='Include in Consolidation', default=True)
    
    exchange_rate = fields.Float(string='Exchange Rate', 
                                help='Exchange rate from company currency to consolidation currency',
                                digits=(12, 6), default=1.0)
    
    @api.constrains('ownership_percentage', 'control_percentage')
    def _check_percentages(self):
        for record in self:
            if record.ownership_percentage < 0 or record.ownership_percentage > 100:
                raise ValidationError(_('Ownership percentage must be between 0 and 100.'))
            if record.control_percentage < 0 or record.control_percentage > 100:
                raise ValidationError(_('Control percentage must be between 0 and 100.'))
    
    def action_extract_data(self):
        self.ensure_one()
        if self.state not in ['draft', 'in_progress']:
            raise UserError(_('You can only extract data for periods in draft or in progress states.'))
        
        # Set state to in progress
        self.write({'state': 'in_progress'})
        
        # Extract trial balance data from the company's accounting
        period = self.period_id
        
        # Get company trial balance data for the period
        trial_balance = self.env['account.general.ledger'].with_context(
            company_id=self.company_id.id,
            date_from=period.date_start,
            date_to=period.date_end
        ).get_report_values()
        
        # Process and convert the data
        self._process_trial_balance(trial_balance)
        
        return True
    
    def _process_trial_balance(self, trial_balance):
        # This method would extract accounting data and convert it according to mapping rules
        # In a real implementation, this would create consolidation entries
        consolidation_journal = self.env['consolidation.journal'].search([
            ('period_id', '=', self.period_id.id),
            ('journal_type', '=', 'extraction'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not consolidation_journal:
            consolidation_journal = self.env['consolidation.journal'].create({
                'name': f'Data Extraction - {self.company_id.name}',
                'period_id': self.period_id.id,
                'journal_type': 'extraction',
                'company_id': self.company_id.id
            })
        
        # Clear existing entries
        consolidation_journal.line_ids.unlink()
        
        # Create new entries based on trial balance
        if 'lines' in trial_balance:
            for line in trial_balance['lines']:
                # Find mapping for this account
                account_code = line.get('code')
                mapping = self.env['consolidation.account.mapping'].search([
                    ('group_id', '=', self.period_id.group_id.id),
                    ('source_account_code', '=', account_code),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
                
                if not mapping:
                    continue
                
                # Convert amounts using exchange rate
                debit = line.get('debit', 0.0) * self.exchange_rate
                credit = line.get('credit', 0.0) * self.exchange_rate
                
                # Create consolidation entry
                self.env['consolidation.journal.line'].create({
                    'journal_id': consolidation_journal.id,
                    'account_id': mapping.target_account_id.id,
                    'name': line.get('name', ''),
                    'debit': debit,
                    'credit': credit,
                    'company_id': self.company_id.id
                })
    
    def action_mark_completed(self):
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('You can only mark completed for periods that are in progress.'))
        
        # Check if data has been extracted
        extraction_journal = self.env['consolidation.journal'].search([
            ('period_id', '=', self.period_id.id),
            ('journal_type', '=', 'extraction'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not extraction_journal or not extraction_journal.line_ids:
            raise UserError(_('You must extract company data before marking the period as completed.'))
        
        # Mark as completed
        self.write({'state': 'completed'})
        return True