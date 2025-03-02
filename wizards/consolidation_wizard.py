# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class ConsolidationWizard(models.TransientModel):
    _name = 'consolidation.wizard'
    _description = 'Consolidation Process Wizard'
    
    group_id = fields.Many2one('consolidation.group', string='Consolidation Group', required=True)
    date_start = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_end = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    name = fields.Char(string='Period Name', required=True, 
                      default=lambda self: 'Consolidation %s' % datetime.now().strftime('%Y-%m'))
    
    company_ids = fields.Many2many('res.company', string='Companies to Include', 
                                  default=lambda self: self._default_companies())
    
    currency_id = fields.Many2one('res.currency', string='Consolidation Currency',
                                 related='group_id.currency_id', readonly=True)
    
    include_intercompany_elimination = fields.Boolean(string='Auto-Eliminate Intercompany Transactions', default=True)
    
    @api.model
    def _default_companies(self):
        if self.env.context.get('active_model') == 'consolidation.group' and self.env.context.get('active_id'):
            group = self.env['consolidation.group'].browse(self.env.context.get('active_id'))
            return group.company_ids
        return self.env.company
    
    @api.onchange('group_id')
    def _onchange_group_id(self):
        if self.group_id:
            self.company_ids = self.group_id.company_ids
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_start > wizard.date_end:
                raise ValidationError(_('Start date must be earlier than end date.'))
    
    def action_create_period(self):
        self.ensure_one()
        
        # Create the consolidation period
        period = self.env['consolidation.period'].create({
            'name': self.name,
            'group_id': self.group_id.id,
            'date_start': self.date_start,
            'date_end': self.date_end,
        })
        
        # Prepare the consolidation
        period.action_prepare_consolidation()
        
        # Update company periods
        for company_period in period.company_period_ids:
            if company_period.company_id not in self.company_ids:
                company_period.include_in_consolidation = False
        
        # Return action to view the created period
        return {
            'name': _('Consolidation Period'),
            'type': 'ir.actions.act_window',
            'res_model': 'consolidation.period',
            'res_id': period.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_extract_all_data(self):
        self.ensure_one()
        
        # Create the period
        action = self.action_create_period()
        period_id = action['res_id']
        period = self.env['consolidation.period'].browse(period_id)
        
        # Extract data for all companies
        for company_period in period.company_period_ids.filtered(
            lambda p: p.include_in_consolidation and p.company_id in self.company_ids):
            try:
                company_period.action_extract_data()
                company_period.action_mark_completed()
            except Exception as e:
                raise UserError(_('Error extracting data for %s: %s') % (company_period.company_id.name, str(e)))
        
        # Apply automatic eliminations if requested
        if self.include_intercompany_elimination:
            elimination_rules = self.env['consolidation.automatic.elimination'].search([
                ('group_id', '=', self.group_id.id),
                ('active', '=', True)
            ])
            for rule in elimination_rules:
                try:
                    rule.action_apply_elimination(period.id)
                except Exception as e:
                    raise UserError(_('Error applying elimination rule %s: %s') % (rule.name, str(e)))
        
        # Return the action to view the period
        return action