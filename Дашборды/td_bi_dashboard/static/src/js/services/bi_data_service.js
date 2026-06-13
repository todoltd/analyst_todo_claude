/** @odoo-module **/
// Part of td_bi_dashboard. Author: ToDo. Since: 19.0.1.0.0
//
// biDataService (реєстр: services "bi_data") — єдиний шлюз даних дашборда.
// Контракт Stage-1:
//   getRuntimeConfig(dashboardId) -> orm.call("td.bi.dashboard","get_runtime_config",[dashboardId])
//   runQuery(datasetId, querySpec) -> orm.call("td.bi.dataset","run_query",[datasetId, querySpec])
// Черга макс 6 паралельних RPC + дебаунс 400 мс на runQuery (ключ = dataset+spec).
// AC-46 — один віджет = рівно один RPC run_query.
// AC-49 — обмеження паралелізму; перевищення/помилка деградує per-віджет, не валить сторінку.

import { registry } from "@web/core/registry";

// Конфігурація черги (ліміти зі специфікації / ARCHITECTURE).
const MAX_PARALLEL_RPC = 6; // AC-49
const DEBOUNCE_MS = 400; // AC-49

export const biDataService = {
    dependencies: ["orm"],

    start(env, { orm }) {
        // --- Стан черги паралелізму ---
        const queue = {
            pending: [], // [{ run, resolve, reject }] — задачі, що чекають слота
            active: 0, // кількість активних RPC (≤ MAX_PARALLEL_RPC)
        };

        // Таймери дебаунсу за ключем запиту (dataset+spec) — AC-46/AC-49.
        const debounceTimers = new Map();

        /**
         * Поставити асинхронну задачу в чергу з обмеженням MAX_PARALLEL_RPC. // AC-49
         * @param {Function} run () => Promise
         * @returns {Promise}
         */
        function enqueue(run) {
            return new Promise((resolve, reject) => {
                queue.pending.push({ run, resolve, reject });
                drain();
            });
        }

        // Запускає наступні задачі, доки є вільні слоти. // AC-49
        function drain() {
            while (queue.active < MAX_PARALLEL_RPC && queue.pending.length) {
                const task = queue.pending.shift();
                queue.active++;
                Promise.resolve()
                    .then(task.run)
                    .then(
                        (res) => {
                            queue.active--;
                            task.resolve(res);
                            drain();
                        },
                        (err) => {
                            queue.active--;
                            // Помилка деградує per-віджет (ловиться у WidgetContainer). // AC-49/AC-52
                            task.reject(err);
                            drain();
                        }
                    );
            }
        }

        /**
         * Повна runtime-конфігурація дашборда одним RPC. // AC-46
         * @param {number} dashboardId
         * @returns {Promise<Object>} {id,name,pages:[...],controls:[...],theme:{}}
         */
        async function getRuntimeConfig(dashboardId) {
            return enqueue(() =>
                orm.call("td.bi.dashboard", "get_runtime_config", [dashboardId])
            );
        }

        /**
         * Один агрегувальний запит даних віджета. // AC-46 (рівно один RPC)
         * Дебаунс 400 мс за ключем (dataset+spec): швидкі повтори (зміна контролів)
         * злипаються в один RPC; черга обмежує паралелізм до 6. // AC-49
         *
         * @param {number} datasetId
         * @param {Object} querySpec {groupby,aggregates,measures,limit,preview,...}
         * @returns {Promise<Object>} {rows:[{keys,values,extra_domains}], totals, meta}
         */
        function runQuery(datasetId, querySpec) {
            const key = `${datasetId}:${JSON.stringify(querySpec || {})}`;
            // Скасувати попередній відкладений виклик з тим самим ключем.
            const prev = debounceTimers.get(key);
            if (prev) {
                clearTimeout(prev.timer);
                // Попередній промис деградуємо тихою відмовою — його віджет уже
                // запросив свіжий стан; не валимо сторінку. // AC-49/AC-52
                prev.reject(new Error("debounced"));
            }
            return new Promise((resolve, reject) => {
                const timer = setTimeout(() => {
                    debounceTimers.delete(key);
                    enqueue(() =>
                        orm.call("td.bi.dataset", "run_query", [datasetId, querySpec])
                    ).then(resolve, reject);
                }, DEBOUNCE_MS);
                debounceTimers.set(key, { timer, reject });
            });
        }

        /**
         * Скасувати всі відкладені (ще не відправлені) запити — при зміні
         * сторінки/контролів. Активні RPC завершуються природньо. // AC-49
         */
        function cancelPending() {
            for (const { timer, reject } of debounceTimers.values()) {
                clearTimeout(timer);
                reject(new Error("cancelled"));
            }
            debounceTimers.clear();
            // Скинути ще не стартовані задачі черги.
            for (const task of queue.pending.splice(0)) {
                task.reject(new Error("cancelled"));
            }
        }

        return {
            getRuntimeConfig,
            runQuery,
            cancelPending,
        };
    },
};

registry.category("services").add("bi_data", biDataService);
