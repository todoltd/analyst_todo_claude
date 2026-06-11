# Odoo Version Notes — API & Convention Differences

Reference for skills that need to interpret or generate version-specific code.

---

## Odoo 16

- Python 3.10+, PostgreSQL 14+
- OWL 2 for frontend (replaces legacy Widget)
- `_check_company` mixin introduced
- `mail.thread` → `mail.thread.main.attachment` split
- Spreadsheet views introduced
- `web.assets_backend` replaces old `web.assets_qweb`
- `res.users.settings` for per-user preferences
- JSON fields supported (`fields.Json`)

## Odoo 17

- Python 3.11+, PostgreSQL 15+
- **Studio customisation stored differently** — `ir.ui.view` arch_fs
- `AccountMove` line grouping refactored (important for accounting modules)
- `product.template` / `product.product` split more pronounced
- `mail.activity.mixin` unchanged but activity view is new default
- `website` module: `http.route` decorator gains `sitemap` param
- New `analytic.mixin` for multi-plan analytics (replaces `account.analytic.line` direct use)
- `_auto_init` deprecated for complex SQL → use `init()` instead

## Odoo 18

- Python 3.12+, PostgreSQL 15+
- **OWL components mandatory** for new views (legacy JS removed)
- `@api.model_create_multi` required on all `create` overrides
- `res.partner` archiving behaviour changed
- `stock.move.line` lot/serial tracking API updated
- `sale.order` → `sale.order.line` discount field moved
- `mail.gateway` refactored — custom mail aliases logic must update
- `ir.actions.server` gains `binding_type` = `'report'` option
- `fields.Html` sanitize default changed to `True`

## Odoo 19

- Python 3.12+, PostgreSQL 16+
- **AI-native fields** — `fields.AiSuggestion` (experimental)
- Multi-company rules enforced more strictly at ORM level
- `account.move` posting: `action_post` → `_post` internal (public API unchanged)
- `product.configurator` fully OWL-based
- `discuss` module decoupled from `mail` — check depends carefully
- `spreadsheet.mixin` stable API (was experimental in 16/17)

---

## Cross-version conventions (all versions)

### Model inheritance patterns
```python
# Extending an existing model
class ResPartner(models.Model):
    _inherit = 'res.partner'

# Creating a new model
class TdProjectTask(models.Model):
    _name = 'td.project.task'
    _description = 'TD Project Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
```

### Deprecated patterns to flag in reverse-spec
- `@api.multi` → removed in v14+, flag if found
- `@api.one` → removed in v14+, flag if found
- `self.env.ref()` inside compute → performance issue, flag
- `_columns = {}` → v7 style, flag as critical tech debt
- `osv.osv` base class → flag as critical tech debt
- Direct SQL in `fields.related` → flag

### Security file format (all versions)
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_td_model_user,td.model user,model_td_model,base.group_user,1,0,0,0
access_td_model_manager,td.model manager,model_td_model,td_module.group_manager,1,1,1,1
```

### Manifest required keys
```python
{
    'name': '',
    'version': '16.0.1.0.0',  # {odoo_version}.{major}.{minor}.{patch}.{fix}
    'category': '',
    'summary': '',
    'author': 'ToDo',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
```
