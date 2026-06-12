# Конфігурація: {module} ({project}) — CONFIG.md (DOC-2)

## Status
<!-- inherited from approved ТР/SPEC — no AI self-approval -->
approved

## Meta
- Source: SPEC.md v{version} (approved) · ALLOCATION.md {today}
- Odoo version / edition: {19 / Community|Enterprise}
- Author: config-spec AI

## Version history
| Date | Author | Change |
|------|--------|--------|
| YYYY-MM-DD | config-spec AI | CONFIG built from approved SPEC «{назва}» |

<!--
RULE: every item below = what to set → exact UI path → expected result → [AC-NN] → Odoo 19 source.
Include only areas that have config ACs; otherwise write "Немає".
Ukrainian wording (the BA executes this); AC-NN / menu paths / technical names exact.
-->

## 1. Застосунки та модулі
| Що активувати | UI-шлях | Очікуваний результат | AC | Джерело Odoo 19 |
|---|---|---|---|---|
| | Apps ▸ … | | AC-01 | §/URL |

## 2. Налаштування (Settings)
| Параметр | UI-шлях | Значення | AC | Джерело |
|---|---|---|---|---|
| | {App} ▸ Settings ▸ … | | | |

## 3. Користувачі, групи, права
| Група / правило | UI-шлях | Призначення | AC | Джерело |
|---|---|---|---|---|
| | Settings ▸ Users & Companies ▸ … | | | |

## 4. Автоматизація (no-code)
| Правило / дія | Тип | Тригер → умова → дія | AC | Джерело |
|---|---|---|---|---|
| | base.automation / server action / cron | | | |

## 5. Подання та форми (Studio)
| Подання | Зміна | Studio/Community | AC | Джерело |
|---|---|---|---|---|
| | | | | |

## 6. Звіти
| Звіт | Макет / фільтри | AC | Джерело |
|---|---|---|---|
| | | | |

## 7. Email та шаблони
| Шаблон (`mail.template`) | Тригер / отримувачі | AC | Джерело |
|---|---|---|---|
| | | | |

## 8. Інтеграції (рівень UI)
| Конектор / налаштування | UI-шлях | Облікові дані (плейсхолдер) | AC | Джерело |
|---|---|---|---|---|
| | | | | |

## 9. Бізнес-правила (config-рівень)
| Правило | Спосіб (Studio constraint / required / domain) | AC | Джерело |
|---|---|---|---|
| | | | |

## 10. Зчеплення з кодом (hybrid)
| AC | Що дає конфігурація | Від якого коду залежить (модель/поле/метод із SPEC) |
|---|---|---|
| AC-03 | | |

## Out of scope
<!-- межі зі SPEC, що стосуються конфігурації -->
-

## Open questions
<!-- пункти, не прив'язані до реальної можливості Odoo 19 — блокують config-review -->
-
