# -*- coding: utf-8 -*-
# Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
# Тести Stage-1 (MVP) за Acceptance criteria SPEC.
# Виконуються на живій Odoo 19:
#   odoo-bin -i td_bi_dashboard --test-enable --stop-after-init
# (або -u td_bi_dashboard для оновлення вже встановленого модуля).
from . import test_dsl_compiler
from . import test_query_security
from . import test_dataset_tree
from . import test_cache_key
from . import test_time_intelligence
from . import test_blend_query
from . import test_show_as
from . import test_alert
from . import test_subscription
