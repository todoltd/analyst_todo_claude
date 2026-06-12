# Odoo Security Groups — Reference

Standard Odoo group XML IDs to reference in SPEC.md user stories and security
tables. Use the **technical XML id** (e.g. `sales_team.group_sale_manager`),
not the human label. Stable across Odoo 16–19, but confirm against the
project's installed modules and version (ToDo convention: verify with Odoo 19
docs when in doubt — see `odoo-version-notes.md`).

## Core (base)

| XML id | Meaning |
|--------|---------|
| `base.group_user` | Internal User (employee) — the default authenticated user |
| `base.group_portal` | Portal user (external, limited) |
| `base.group_public` | Public / website visitor (not logged in) |
| `base.group_system` | Settings / Administrator (full config access) |
| `base.group_erp_manager` | Access Rights manager |
| `base.group_no_one` | Technical Features (hidden advanced options) |
| `base.group_multi_company` | Multi-company toggle |
| `base.group_multi_currency` | Multi-currency toggle |

## Sales / CRM
| XML id | Meaning |
|--------|---------|
| `sales_team.group_sale_salesman` | Salesperson (own documents) |
| `sales_team.group_sale_salesman_all_leads` | Salesperson — all documents |
| `sales_team.group_sale_manager` | Sales Manager |

## Accounting
| XML id | Meaning |
|--------|---------|
| `account.group_account_invoice` | Billing |
| `account.group_account_user` | Accountant |
| `account.group_account_manager` | Accounting Manager (full) |
| `account.group_account_readonly` | Read-only |

## Inventory (stock)
| XML id | Meaning |
|--------|---------|
| `stock.group_stock_user` | Inventory User |
| `stock.group_stock_manager` | Inventory Manager |
| `stock.group_stock_multi_locations` | Multi-locations |
| `stock.group_production_lot` | Lots & Serial Numbers |

## Purchase
| XML id | Meaning |
|--------|---------|
| `purchase.group_purchase_user` | Purchase User |
| `purchase.group_purchase_manager` | Purchase Manager |

## Manufacturing (mrp)
| XML id | Meaning |
|--------|---------|
| `mrp.group_mrp_user` | Manufacturing User |
| `mrp.group_mrp_manager` | Manufacturing Manager |

## HR
| XML id | Meaning |
|--------|---------|
| `hr.group_hr_user` | Officer |
| `hr.group_hr_manager` | HR Manager |

## Project
| XML id | Meaning |
|--------|---------|
| `project.group_project_user` | Project User |
| `project.group_project_manager` | Project Manager |

## Website
| XML id | Meaning |
|--------|---------|
| `website.group_website_restricted_editor` | Editor / Publisher |
| `website.group_website_designer` | Designer (full website access) |

---

## ToDo custom-module group convention

New `td_*` / `<project>_<area>` modules define their **own** category + two
groups (matches the `scaffolding` security template):

```xml
<record id="module_category_{module}" model="ir.module.category">
    <field name="name">{Human Module Name}</field>
</record>

<record id="group_{module}_user" model="res.groups">
    <field name="name">User</field>
    <field name="category_id" ref="module_category_{module}"/>
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
</record>

<record id="group_{module}_manager" model="res.groups">
    <field name="name">Manager</field>
    <field name="category_id" ref="module_category_{module}"/>
    <field name="implied_ids" eval="[(4, ref('group_{module}_user'))]"/>
</record>
```

Rules:
- `group_{module}_user` always implies `base.group_user`.
- `group_{module}_manager` always implies `group_{module}_user`.
- In SPEC.md security tables, reference these as `{module}.group_{module}_user`
  and `{module}.group_{module}_manager`.
- Map every user story role to one of: a standard group above, or a custom
  group defined by this module. Never invent group IDs.
